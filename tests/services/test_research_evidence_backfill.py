from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.domain.models import (
    DailyBar,
    Exchange,
    FundamentalSnapshot,
    Instrument,
    InstrumentUniverseSync,
    Market,
    ResearchEvidenceBackfill,
    TechnicalIndicator,
)
from packages.services.research_evidence_backfill import (
    BackfillRequest,
    create_backfill_run,
    create_resume_backfill_run,
    execute_backfill_run,
    get_evidence_coverage,
    request_cancel_backfill,
)
from packages.providers.base import ProviderBar
from packages.services.daily_bar_sources import DailyBarFetchCoordinator, DailyBarSource
from packages.shared.database import Base


@pytest.fixture
def session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    database_session = sessionmaker(bind=engine)()
    try:
        yield database_session
    finally:
        database_session.close()
        Base.metadata.drop_all(engine)


def seed_universe(session: Session, symbols_per_exchange: int = 3) -> None:
    market = Market(
        code="CN",
        name="China A Share",
        timezone="Asia/Shanghai",
        currency="CNY",
    )
    session.add(market)
    session.flush()
    prefixes = {"SSE": "600", "SZSE": "000", "BSE": "830"}
    for exchange_code, prefix in prefixes.items():
        exchange = Exchange(
            market_id=market.id,
            code=exchange_code,
            name=exchange_code,
        )
        session.add(exchange)
        session.flush()
        for index in range(symbols_per_exchange):
            session.add(
                Instrument(
                    symbol=f"{prefix}{index:03d}",
                    name=f"{exchange_code} {index}",
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
            total_count=symbols_per_exchange * 3,
            inserted_count=symbols_per_exchange * 3,
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


def test_create_canary_freezes_deterministic_multi_exchange_scope(session: Session):
    seed_universe(session)

    payload = create_backfill_run(
        BackfillRequest(
            run_kind="canary",
            start_date=date(2025, 1, 1),
            end_date=date(2026, 7, 10),
            cohort_size=6,
        ),
        session=session,
    )
    duplicate = create_backfill_run(
        BackfillRequest(
            run_kind="baseline",
            start_date=date(2025, 1, 1),
            end_date=date(2026, 7, 10),
        ),
        session=session,
    )

    assert payload["status"] == "created"
    assert payload["item"]["scope_symbols"] == [
        "830000",
        "830001",
        "600000",
        "600001",
        "000000",
        "000001",
    ]
    assert payload["item"]["universe_sync_id"]
    assert payload["item"]["daily_bar_policy"] == "strict"
    assert payload["item"]["source_stats"] == {}
    assert duplicate["status"] == "already_running"
    assert duplicate["item"]["id"] == payload["item"]["id"]


def test_execute_backfill_classifies_partial_success_and_keeps_retry_sets(
    session: Session,
    monkeypatch,
):
    seed_universe(session, symbols_per_exchange=1)
    payload = create_backfill_run(
        BackfillRequest(
            run_kind="canary",
            start_date=date(2025, 1, 1),
            end_date=date(2026, 7, 10),
            cohort_size=3,
            batch_size=2,
        ),
        session=session,
    )
    failing_symbol = "600000"

    def fake_bars(**kwargs):
        if kwargs["symbol"] == failing_symbol:
            raise TimeoutError("upstream timed out")
        return {"status": "ingested", "bar_count": 360}

    monkeypatch.setattr(
        "packages.services.research_evidence_backfill.ingest_symbol_daily_bars",
        fake_bars,
    )
    monkeypatch.setattr(
        "packages.services.research_evidence_backfill.ingest_fundamentals",
        lambda *args, **kwargs: {"status": "ingested"},
    )
    monkeypatch.setattr(
        "packages.services.research_evidence_backfill.calculate_and_store_daily_indicators",
        lambda *args, **kwargs: {"status": "calculated", "indicator_count": 12},
    )

    result = execute_backfill_run(payload["item"]["id"], session=session)

    assert result["status"] == "partial"
    assert result["phase"] == "completed"
    assert result["counters"]["daily_bars"] == {
        "attempted": 3,
        "succeeded": 2,
        "no_data": 0,
        "insufficient_data": 0,
        "failed": 1,
    }
    assert result["counters"]["fundamentals"]["succeeded"] == 3
    assert result["counters"]["technical_indicators"]["succeeded"] == 3
    assert result["retry"]["daily_bars"] == [failing_symbol]
    assert result["diagnostics"][0]["code"] == "TIMEOUT"
    assert "upstream timed out" not in str(result["diagnostics"])


def test_resilient_policy_is_preserved_in_created_run(session: Session):
    seed_universe(session)

    payload = create_backfill_run(
        BackfillRequest(
            run_kind="canary",
            daily_bar_policy="cn_resilient",
            start_date=date(2025, 1, 1),
            end_date=date(2026, 7, 10),
            cohort_size=3,
        ),
        session=session,
    )

    assert payload["item"]["daily_bar_policy"] == "cn_resilient"


def test_resilient_backfill_persists_source_stats_across_symbols(
    session: Session,
    monkeypatch,
):
    seed_universe(session, symbols_per_exchange=1)
    payload = create_backfill_run(
        BackfillRequest(
            run_kind="canary",
            daily_bar_policy="cn_resilient",
            evidence_kinds=("daily_bars",),
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 10),
            cohort_size=3,
        ),
        session=session,
    )

    def fallback_bars(symbol, _timeframe, _start, _end):
        return [
            ProviderBar(
                symbol=symbol,
                timestamp=date(2026, 7, 9),
                open=Decimal("10"),
                high=Decimal("11"),
                low=Decimal("9"),
                close=Decimal("10"),
                volume=Decimal("1000"),
                amount=Decimal("10000"),
            )
        ]

    coordinator = DailyBarFetchCoordinator(
        [
            DailyBarSource(
                provider="akshare",
                source="akshare.stock_zh_a_hist",
                adjustment="qfq",
                priority=0,
                fetch=lambda *_args: (_ for _ in ()).throw(ConnectionError("unavailable")),
            ),
            DailyBarSource(
                provider="akshare",
                source="akshare.stock_zh_a_daily",
                adjustment="qfq",
                priority=1,
                fetch=fallback_bars,
            ),
        ]
    )
    monkeypatch.setattr(
        "packages.services.research_evidence_backfill.build_daily_bar_fetch_coordinator",
        lambda _provider: coordinator,
    )

    result = execute_backfill_run(payload["item"]["id"], session=session)

    assert result["status"] == "succeeded"
    assert result["source_stats"]["akshare.stock_zh_a_hist"]["failed"] == 3
    assert result["source_stats"]["akshare.stock_zh_a_daily"]["selected"] == 3
    assert session.query(DailyBar).count() == 3
    assert {bar.source for bar in session.query(DailyBar).all()} == {
        "akshare.stock_zh_a_daily"
    }


def test_cancelled_run_stops_before_processing_and_preserves_checkpoint(
    session: Session,
    monkeypatch,
):
    seed_universe(session, symbols_per_exchange=1)
    payload = create_backfill_run(
        BackfillRequest(
            run_kind="canary",
            start_date=date(2025, 1, 1),
            end_date=date(2026, 7, 10),
            cohort_size=3,
        ),
        session=session,
    )
    request_cancel_backfill(payload["item"]["id"], session=session)
    monkeypatch.setattr(
        "packages.services.research_evidence_backfill.ingest_symbol_daily_bars",
        lambda **kwargs: pytest.fail("cancelled run must not call the provider"),
    )

    result = execute_backfill_run(payload["item"]["id"], session=session)

    assert result["status"] == "cancelled"
    assert result["cursor"] == 0
    assert result["processed_count"] == 0


def test_transient_provider_failures_use_bounded_exponential_retry(
    session: Session,
    monkeypatch,
):
    seed_universe(session, symbols_per_exchange=1)
    payload = create_backfill_run(
        BackfillRequest(
            run_kind="canary",
            evidence_kinds=("daily_bars",),
            start_date=date(2025, 1, 1),
            end_date=date(2026, 7, 10),
            cohort_size=3,
        ),
        session=session,
    )
    attempts = 0
    sleeps: list[float] = []

    def flaky_bars(**_kwargs):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise TimeoutError("temporary timeout")
        return {"status": "ingested", "bar_count": 360}

    monkeypatch.setattr(
        "packages.services.research_evidence_backfill.ingest_symbol_daily_bars",
        flaky_bars,
    )

    result = execute_backfill_run(
        payload["item"]["id"],
        session=session,
        max_transient_attempts=3,
        retry_base_seconds=1.0,
        sleep_fn=sleeps.append,
    )

    assert result["status"] == "succeeded"
    assert attempts == 5
    assert sleeps == [1.0, 2.0]


def test_resume_run_copies_checkpoint_and_lineage(session: Session):
    seed_universe(session, symbols_per_exchange=2)
    original_payload = create_backfill_run(
        BackfillRequest(
            run_kind="baseline",
            start_date=date(2025, 1, 1),
            end_date=date(2026, 7, 10),
            batch_size=2,
        ),
        session=session,
    )
    original = session.get(
        ResearchEvidenceBackfill,
        UUID(original_payload["item"]["id"]),
    )
    assert original is not None
    original.status = "failed"
    original.phase = "daily_bars"
    original.cursor = 2
    original.processed_count = 2
    original.counters_json = {
        "daily_bars": {
            "attempted": 2,
            "succeeded": 2,
            "no_data": 0,
            "insufficient_data": 0,
            "failed": 0,
        }
    }
    session.commit()

    resumed = create_resume_backfill_run(str(original.id), session=session)

    assert resumed["status"] == "created"
    assert resumed["item"]["parent_run_id"] == str(original.id)
    assert resumed["item"]["phase"] == "daily_bars"
    assert resumed["item"]["cursor"] == 2
    assert resumed["item"]["processed_count"] == 2
    assert resumed["item"]["scope_symbols"] == original.scope_symbols_json


def test_evidence_coverage_reports_thresholds_and_exchange_breakdown(session: Session):
    seed_universe(session, symbols_per_exchange=1)
    instruments = session.query(Instrument).order_by(Instrument.symbol).all()
    ready_symbols = {"600000", "830000"}
    for instrument in instruments:
        if instrument.symbol not in ready_symbols:
            continue
        for offset in range(35):
            trade_date = date(2026, 5, 25).fromordinal(date(2026, 5, 25).toordinal() + offset)
            session.add(
                DailyBar(
                    instrument_id=instrument.id,
                    trade_date=trade_date,
                    open=10,
                    high=11,
                    low=9,
                    close=10,
                    volume=1_000_000,
                    amount=10_000_000,
                )
            )
        for code in ("ma", "rsi", "mfi"):
            session.add(
                TechnicalIndicator(
                    instrument_id=instrument.id,
                    timeframe="1d",
                    as_of=datetime(2026, 6, 28, tzinfo=timezone.utc),
                    indicator_code=code,
                    params={},
                    value_json={"value": 50},
                )
            )
        session.add(
            FundamentalSnapshot(
                symbol=instrument.symbol,
                as_of=date(2026, 3, 31),
                currency="CNY",
                pe_ratio=20,
                revenue_growth=0.1,
                net_margin=0.12,
                debt_to_assets=0.4,
                source="akshare",
            )
        )
    session.commit()

    payload = get_evidence_coverage(
        session=session,
        market="CN",
        provider="akshare",
        as_of=date(2026, 7, 1),
    )

    assert payload["universe"]["active_count"] == 3
    assert payload["universe"]["exchange_counts"] == {"BSE": 1, "SSE": 1, "SZSE": 1}
    assert payload["evidence"]["daily_bars"]["ready_count"] == 2
    assert payload["evidence"]["technical_indicators"]["ready_count"] == 2
    assert payload["evidence"]["fundamentals"]["ready_count"] == 2
    assert payload["evidence"]["daily_bars"]["passes_threshold"] is False
    assert payload["evidence"]["daily_bars"]["by_exchange"]["SZSE"]["ready_count"] == 0
    assert payload["evidence"]["daily_bars"]["source_distribution"] == [
        {
            "provider": "legacy_unknown",
            "source": "legacy_unknown",
            "row_count": 70,
            "instrument_count": 2,
        }
    ]
    assert payload["status"] == "needs_attention"


def test_evidence_coverage_as_of_ignores_future_indicator_and_fundamental_rows(
    session: Session,
):
    seed_universe(session, symbols_per_exchange=1)
    instruments = session.query(Instrument).order_by(Instrument.symbol).all()
    decision_date = date(2026, 7, 1)
    for instrument in instruments:
        if instrument.symbol == "600000":
            for code in ("ma", "rsi", "mfi"):
                session.add(
                    TechnicalIndicator(
                        instrument_id=instrument.id,
                        timeframe="1d",
                        as_of=datetime(2026, 6, 30, tzinfo=timezone.utc),
                        indicator_code=code,
                        params={},
                        value_json={"value": 50},
                    )
                )
            session.add(
                FundamentalSnapshot(
                    symbol=instrument.symbol,
                    as_of=date(2026, 6, 30),
                    currency="CNY",
                    pe_ratio=20,
                    revenue_growth=0.1,
                    net_margin=0.12,
                    debt_to_assets=0.4,
                    source="point_in_time_fixture",
                )
            )
        for code in ("ma", "rsi", "mfi"):
            session.add(
                TechnicalIndicator(
                    instrument_id=instrument.id,
                    timeframe="1d",
                    as_of=datetime(2026, 7, 2, tzinfo=timezone.utc),
                    indicator_code=code,
                    params={},
                    value_json={"value": 80},
                )
            )
        session.add(
            FundamentalSnapshot(
                symbol=instrument.symbol,
                as_of=date(2026, 7, 2),
                currency="CNY",
                pe_ratio=10,
                revenue_growth=0.2,
                net_margin=0.2,
                debt_to_assets=0.2,
                source="future_fixture",
            )
        )
    session.commit()

    payload = get_evidence_coverage(
        session=session,
        market="CN",
        provider="akshare",
        as_of=decision_date,
    )

    assert payload["evidence"]["technical_indicators"]["ready_count"] == 1
    assert payload["evidence"]["fundamentals"]["ready_count"] == 1
    assert payload["evidence"]["technical_indicators"]["threshold"] == 0.90
    assert payload["evidence"]["fundamentals"]["threshold"] == 0.80
    assert payload["thresholds"] == {
        "daily_bars": 0.95,
        "technical_indicators": 0.90,
        "fundamentals": 0.80,
    }


def test_evidence_coverage_query_count_is_constant_for_large_universe(session: Session):
    seed_universe(session, symbols_per_exchange=50)
    select_count = 0

    def count_selects(_connection, _cursor, statement, _parameters, _context, _many):
        nonlocal select_count
        if statement.lstrip().upper().startswith("SELECT"):
            select_count += 1

    event.listen(session.get_bind(), "before_cursor_execute", count_selects)
    try:
        payload = get_evidence_coverage(
            session=session,
            market="CN",
            provider="akshare",
            as_of=date(2026, 7, 1),
        )
    finally:
        event.remove(session.get_bind(), "before_cursor_execute", count_selects)

    assert payload["universe"]["active_count"] == 150
    assert select_count <= 5
