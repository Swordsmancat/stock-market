from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from apps.api.main import app
from packages.domain.models import Exchange, Instrument, InstrumentUniverseSync, Market
from packages.providers.base import ProviderInstrument, ProviderInstrumentUniverseSnapshot
from packages.services import instrument_universe as instrument_universe_service
from packages.shared.database import Base, get_session
from tests.helpers.celery_sync import dispatch_task_run_sync


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_ingestion_api_dispatches_task_run_and_writes_database(monkeypatch):
    session = make_session()
    monkeypatch.setattr(
        "packages.services.task_dispatch.dispatch_task_run",
        lambda task_name, input_json, task_run_id: dispatch_task_run_sync(
            task_name,
            input_json,
            task_run_id,
            session,
        ),
    )

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        ingest_response = client.post(
            "/ingestion/snapshot",
            params={
                "market": "US",
                "provider": "mock",
                "start": "2026-01-01",
                "end": "2026-01-02",
            },
        )
        bars_response = client.get(
            "/market-data/AAPL/bars",
            params={"timeframe": "1d", "start": "2026-01-01", "end": "2026-01-02"},
        )
    finally:
        app.dependency_overrides.clear()

    assert ingest_response.status_code == 200
    ingest_payload = ingest_response.json()
    assert ingest_payload["status"] == "dispatched"
    task_run = ingest_payload["task_run"]
    assert task_run["task_name"] == "ingestion.ingest_market_data"
    assert task_run["status"] == "succeeded"
    result = task_run["result_json"]
    assert result["status"] == "ingested"
    assert result["market"] == "US"
    assert result["bar_count"] == 2

    assert bars_response.status_code == 200
    bars_payload = bars_response.json()
    assert bars_payload["source"] == "database"
    assert len(bars_payload["items"]) == 2
    assert bars_payload["items"][-1]["close"] == 102.0


def test_instrument_universe_api_dispatches_sync_and_reports_coverage(monkeypatch):
    session = make_session()
    monkeypatch.setattr(
        "packages.services.task_dispatch.dispatch_task_run",
        lambda task_name, input_json, task_run_id: dispatch_task_run_sync(
            task_name,
            input_json,
            task_run_id,
            session,
        ),
    )

    class FakeUniverseProvider:
        def fetch_instrument_universe(self, market: str) -> ProviderInstrumentUniverseSnapshot:
            assert market == "CN"
            return ProviderInstrumentUniverseSnapshot(
                provider="akshare",
                source="akshare.fixture",
                as_of=datetime(2026, 7, 10, tzinfo=timezone.utc),
                status="ok",
                items=[
                    ProviderInstrument(
                        symbol="600519",
                        name="Kweichow Moutai",
                        market="CN",
                        exchange="SSE",
                        asset_type="stock",
                        currency="CNY",
                    )
                ],
                is_complete=True,
                availability={"status": "ok", "row_count": 1},
            )

    def fake_sync(**kwargs):
        return instrument_universe_service.sync_instrument_universe(
            session=kwargs["session"],
            market=kwargs["market"],
            provider_name=kwargs["provider_name"],
            provider=FakeUniverseProvider(),
        )

    monkeypatch.setattr(
        "apps.worker.tasks.ingestion.sync_instrument_universe",
        fake_sync,
    )

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        sync_response = client.post("/ingestion/instrument-universe")
        status_response = client.get("/ingestion/instrument-universe/status")
    finally:
        app.dependency_overrides.clear()

    assert sync_response.status_code == 200
    task_run = sync_response.json()["task_run"]
    assert task_run["task_name"] == "ingestion.sync_instrument_universe"
    assert task_run["status"] == "succeeded"
    assert task_run["result_json"]["counts"]["inserted_count"] == 1
    assert task_run["result_json"]["progress"]["phase"] == "completed"

    assert status_response.status_code == 200
    status = status_response.json()
    assert status["status"] == "ok"
    assert status["active_instrument_count"] == 1
    assert status["managed_instrument_count"] == 1


def test_instrument_universe_status_api_rejects_unsupported_market():
    client = TestClient(app)

    response = client.get(
        "/ingestion/instrument-universe/status",
        params={"market": "US"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported instrument universe market: US"


def test_cn_fund_index_pipeline_api_dispatches_bounded_task(monkeypatch):
    session = make_session()
    captured = {}

    def fake_dispatch(task_name, input_json, task_run_id):
        captured.update(
            task_name=task_name,
            input_json=input_json,
            task_run_id=task_run_id,
        )
        return "celery-fund-index"

    monkeypatch.setattr(
        "packages.services.task_dispatch.dispatch_task_run",
        fake_dispatch,
    )

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        response = TestClient(app).post(
            "/ingestion/cn-fund-index-pipeline",
            params={"lookback_days": 90, "max_symbols_per_type": 2500},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "dispatched"
    assert captured["task_name"] == "ingestion.sync_cn_fund_index_data"
    assert captured["input_json"]["asset_types"] == ["etf", "index"]
    assert captured["input_json"]["lookback_days"] == 90
    assert captured["input_json"]["max_symbols_per_type"] == 2500


def test_corporate_action_api_dispatches_normalized_batch_task(monkeypatch):
    session = make_session()
    monkeypatch.setattr(
        "packages.services.task_dispatch.dispatch_task_run",
        lambda task_name, input_json, task_run_id: dispatch_task_run_sync(
            task_name,
            input_json,
            task_run_id,
            session,
        ),
    )

    def fake_sync(payload, *, session, progress_callback):
        progress_callback("persisted", 3, 3, "Persisted batch.")
        return {
            "status": "ok",
            "report_period": payload.report_period.isoformat(),
            "symbols": list(payload.symbols),
            "event_types": list(payload.event_types),
            "next_cursor": None,
            "retry": {"failed_event_types": []},
        }

    monkeypatch.setattr(
        "apps.worker.tasks.ingestion.sync_corporate_action_evidence",
        fake_sync,
    )

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        response = client.post(
            "/ingestion/corporate-actions",
            json={
                "report_period": "2025-12-31",
                "symbols": ["600519", "600519"],
                "event_types": ["dividend_bonus", "rights_allotment"],
                "cursor": 0,
                "batch_size": 50,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "dispatched"
    task_run = payload["task_run"]
    assert task_run["task_name"] == "ingestion.sync_corporate_actions"
    assert task_run["input_json"]["symbols"] == ["600519"]
    assert task_run["status"] == "succeeded"
    assert task_run["result_json"]["progress"]["phase"] == "completed"


def test_symbol_daily_bars_ingestion_dispatches_task_run_and_writes_database(monkeypatch):
    session = make_session()
    monkeypatch.setattr(
        "packages.services.task_dispatch.dispatch_task_run",
        lambda task_name, input_json, task_run_id: dispatch_task_run_sync(
            task_name,
            input_json,
            task_run_id,
            session,
        ),
    )

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        ingest_response = client.post(
            "/ingestion/symbol-daily-bars",
            params={
                "symbol": "aapl",
                "market": "us",
                "provider": "mock",
                "start": "2026-01-01",
                "end": "2026-01-02",
                "asset_type": "etf",
            },
        )
        bars_response = client.get(
            "/market-data/AAPL/bars",
            params={
                "timeframe": "1d",
                "start": "2026-01-01",
                "end": "2026-01-02",
                "provider": "mock",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert ingest_response.status_code == 200
    ingest_payload = ingest_response.json()
    assert ingest_payload["status"] == "dispatched"
    task_run = ingest_payload["task_run"]
    assert task_run["task_name"] == "ingestion.ingest_symbol_daily_bars"
    assert task_run["status"] == "succeeded"
    assert task_run["input_json"]["symbol"] == "AAPL"
    assert task_run["input_json"]["market"] == "US"
    assert task_run["input_json"]["asset_type"] == "etf"

    result = task_run["result_json"]
    assert result["status"] == "ingested"
    assert result["symbol"] == "AAPL"
    assert result["market"] == "US"
    assert result["asset_type"] == "etf"
    assert result["provider"] == "mock"
    assert result["bar_count"] == 2

    assert bars_response.status_code == 200
    bars_payload = bars_response.json()
    assert bars_payload["source"] == "database"
    assert len(bars_payload["items"]) == 2
    assert bars_payload["items"][-1]["close"] == 102.0


def test_symbol_daily_bars_batch_ingestion_dispatches_task_run_and_writes_database(
    monkeypatch,
):
    session = make_session()
    monkeypatch.setattr(
        "packages.services.task_dispatch.dispatch_task_run",
        lambda task_name, input_json, task_run_id: dispatch_task_run_sync(
            task_name,
            input_json,
            task_run_id,
            session,
        ),
    )

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        ingest_response = client.post(
            "/ingestion/symbol-daily-bars-batch",
            params={
                "symbols": "aapl,msft,aapl",
                "market": "us",
                "provider": "mock",
                "start": "2026-01-01",
                "end": "2026-01-02",
                "asset_type": "etf",
            },
        )
        bars_response = client.get(
            "/market-data/MSFT/bars",
            params={
                "timeframe": "1d",
                "start": "2026-01-01",
                "end": "2026-01-02",
                "provider": "mock",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert ingest_response.status_code == 200
    ingest_payload = ingest_response.json()
    assert ingest_payload["status"] == "dispatched"
    task_run = ingest_payload["task_run"]
    assert task_run["task_name"] == "ingestion.ingest_symbol_daily_bars_batch"
    assert task_run["status"] == "succeeded"
    assert task_run["input_json"]["symbols"] == ["AAPL", "MSFT"]
    assert task_run["input_json"]["asset_type"] == "etf"

    result = task_run["result_json"]
    assert result["status"] == "ingested"
    assert result["symbols"] == ["AAPL", "MSFT"]
    assert result["symbol_count"] == 2
    assert result["succeeded_count"] == 2
    assert result["total_bar_count"] == 4
    assert result["asset_type"] == "etf"

    assert bars_response.status_code == 200
    bars_payload = bars_response.json()
    assert bars_payload["source"] == "database"
    assert len(bars_payload["items"]) == 2
    assert bars_payload["items"][-1]["close"] == 102.0


def test_symbol_daily_bars_batch_ingestion_rejects_empty_symbols():
    client = TestClient(app)

    response = client.post(
        "/ingestion/symbol-daily-bars-batch",
        params={
            "symbols": " , ,, ",
            "market": "us",
            "provider": "mock",
            "start": "2026-01-01",
            "end": "2026-01-02",
        },
    )

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "At least one symbol is required for batch daily bar ingestion."
    )


def test_legacy_mock_snapshot_endpoint_remains_compatible(monkeypatch):
    session = make_session()
    monkeypatch.setattr(
        "packages.services.task_dispatch.dispatch_task_run",
        lambda task_name, input_json, task_run_id: dispatch_task_run_sync(
            task_name,
            input_json,
            task_run_id,
            session,
        ),
    )

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        response = client.post(
            "/ingestion/mock-snapshot",
            params={
                "market": "US",
                "provider": "mock",
                "start": "2026-01-01",
                "end": "2026-01-02",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "dispatched"
    assert payload["task_run"]["task_name"] == "ingestion.ingest_market_data"


def test_research_evidence_backfill_api_dispatches_and_reports_coverage(monkeypatch):
    session = make_session()
    market = Market(
        code="CN",
        name="China A Share",
        timezone="Asia/Shanghai",
        currency="CNY",
    )
    session.add(market)
    session.flush()
    for exchange_code, symbol in (("SSE", "600000"), ("SZSE", "000001"), ("BSE", "830001")):
        exchange = Exchange(market_id=market.id, code=exchange_code, name=exchange_code)
        session.add(exchange)
        session.flush()
        session.add(
            Instrument(
                symbol=symbol,
                name=symbol,
                market_id=market.id,
                exchange_id=exchange.id,
                asset_type="stock",
                currency="CNY",
                is_active=True,
                universe_provider="akshare",
            )
        )
    session.add(
        InstrumentUniverseSync(
            market="CN",
            provider="akshare",
            source="akshare.stock_info_a_code_name",
            as_of=datetime(2026, 7, 10, tzinfo=timezone.utc),
            status="ok",
            total_count=3,
            inserted_count=3,
            updated_count=0,
            unchanged_count=0,
            reactivated_count=0,
            deactivated_count=0,
            skipped_count=0,
            availability_json={"status": "ok"},
            diagnostics_json=[],
        )
    )
    session.commit()
    monkeypatch.setattr(
        "packages.services.task_dispatch.dispatch_task_run",
        lambda task_name, input_json, task_run_id: dispatch_task_run_sync(
            task_name,
            input_json,
            task_run_id,
            session,
        ),
    )
    monkeypatch.setattr(
        "apps.worker.tasks.ingestion.settings.a_share_backfill_request_delay_ms",
        0,
    )
    monkeypatch.setattr(
        "apps.worker.tasks.ingestion.settings.a_share_backfill_max_transient_attempts",
        1,
    )
    monkeypatch.setattr(
        "packages.services.research_evidence_backfill.ingest_symbol_daily_bars",
        lambda **kwargs: {"status": "no_data", "bar_count": 0},
    )
    monkeypatch.setattr(
        "packages.services.research_evidence_backfill.ingest_fundamentals",
        lambda *args, **kwargs: {"status": "empty"},
    )
    monkeypatch.setattr(
        "packages.services.research_evidence_backfill.calculate_and_store_daily_indicators",
        lambda *args, **kwargs: {"status": "no_data", "indicator_count": 0},
    )

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        response = client.post(
            "/ingestion/a-share-evidence-backfills",
            json={
                "run_kind": "canary",
                "daily_bar_policy": "cn_resilient",
                "start_date": date(2025, 1, 1).isoformat(),
                "end_date": date(2026, 7, 10).isoformat(),
                "cohort_size": 3,
                "batch_size": 2,
            },
        )
        coverage_response = client.get("/stock-selection/evidence-coverage")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "dispatched"
    assert payload["task_run"]["status"] == "succeeded"
    assert payload["backfill"]["status"] == "succeeded"
    assert payload["backfill"]["daily_bar_policy"] == "cn_resilient"
    assert payload["backfill"]["processed_count"] == 9
    assert coverage_response.status_code == 200
    coverage = coverage_response.json()
    assert coverage["universe"]["exchange_counts"] == {"BSE": 1, "SSE": 1, "SZSE": 1}
    assert coverage["status"] == "needs_attention"
