from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

import packages.domain.models  # noqa: F401
from apps.worker.tasks.ingestion import ingest_mock_market_data
from apps.worker.tasks import reports as report_tasks
from packages.services.reports import get_latest_daily_report_payload
from packages.services.task_runs import get_latest_task_run_payload
from packages.services.watchlists import upsert_watchlist_item
from packages.shared.database import Base


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_ingest_market_data_records_succeeded_task_run(monkeypatch):
    session = make_session()
    from apps.worker.tasks import ingestion as ingestion_tasks

    monkeypatch.setattr(ingestion_tasks, "SessionLocal", lambda: session)

    result = ingestion_tasks.ingest_market_data(
        market="US",
        start="2026-01-01",
        end="2026-01-02",
        provider="mock",
    )
    latest_run = get_latest_task_run_payload(
        session=session,
        task_name="ingestion.ingest_market_data",
    )

    assert result["status"] == "ingested"
    assert result["bar_count"] == 2
    assert latest_run["status"] == "succeeded"
    assert latest_run["result_json"]["bar_count"] == 2


def test_sync_instrument_universe_task_records_progress_and_success(monkeypatch):
    session = make_session()
    from apps.worker.tasks import ingestion as ingestion_tasks

    monkeypatch.setattr(ingestion_tasks, "SessionLocal", lambda: session)
    monkeypatch.setattr(
        ingestion_tasks,
        "sync_instrument_universe",
        lambda **_kwargs: {
            "status": "ok",
            "market": "CN",
            "provider": "akshare",
            "source": "akshare.fixture",
            "is_complete": True,
            "counts": {"total_count": 3},
            "diagnostics": [],
            "sync": {"status": "ok"},
            "safety": {"failed_refresh_preserves_last_good_universe": True},
        },
    )

    result = ingestion_tasks.sync_instrument_universe_task()
    latest_run = get_latest_task_run_payload(
        session=session,
        task_name="ingestion.sync_instrument_universe",
    )

    assert result["status"] == "ok"
    assert result["progress"]["phase"] == "completed"
    assert latest_run["status"] == "succeeded"
    assert latest_run["result_json"] == result


def test_sync_instrument_universe_task_marks_provider_failure(monkeypatch):
    session = make_session()
    from apps.worker.tasks import ingestion as ingestion_tasks

    monkeypatch.setattr(ingestion_tasks, "SessionLocal", lambda: session)
    monkeypatch.setattr(
        ingestion_tasks,
        "sync_instrument_universe",
        lambda **_kwargs: {
            "status": "failed",
            "market": "CN",
            "provider": "akshare",
        },
    )

    with pytest.raises(RuntimeError, match="last good universe was preserved"):
        ingestion_tasks.sync_instrument_universe_task()
    latest_run = get_latest_task_run_payload(
        session=session,
        task_name="ingestion.sync_instrument_universe",
    )

    assert latest_run["status"] == "failed"
    assert "last good universe was preserved" in latest_run["error_message"]


def test_sync_corporate_actions_task_records_partial_batch_and_progress(monkeypatch):
    session = make_session()
    from apps.worker.tasks import ingestion as ingestion_tasks

    monkeypatch.setattr(ingestion_tasks, "SessionLocal", lambda: session)

    def fake_sync(payload, *, session, progress_callback):
        assert payload.report_period == date(2025, 12, 31)
        assert payload.symbols == ("600519",)
        progress_callback("preparing", 0, 3, "Preparing batch.")
        progress_callback("persisted", 3, 3, "Persisted batch.")
        return {
            "status": "partial",
            "symbols": ["600519"],
            "event_types": ["dividend_bonus", "rights_allotment"],
            "next_cursor": None,
            "retry": {"failed_event_types": ["rights_allotment"]},
        }

    monkeypatch.setattr(ingestion_tasks, "sync_corporate_action_evidence", fake_sync)

    result = ingestion_tasks.sync_corporate_actions_task(
        report_period="2025-12-31",
        symbols=["600519"],
    )
    latest_run = get_latest_task_run_payload(
        session=session,
        task_name="ingestion.sync_corporate_actions",
    )

    assert result["status"] == "partial"
    assert result["progress"]["phase"] == "completed"
    assert latest_run["status"] == "succeeded"
    assert latest_run["result_json"] == result


@pytest.mark.parametrize("quality_status", ["WARN", "FAIL"])
def test_ingest_market_data_persists_quality_diagnostics_without_failing_task_run(
    monkeypatch,
    quality_status,
):
    session = make_session()
    from apps.worker.tasks import ingestion as ingestion_tasks

    quality_diagnostics = {
        "status": quality_status,
        "instrument_count": 1,
        "instruments": [
            {
                "symbol": "AAPL",
                "status": quality_status,
                "checked_bars": 2,
                "missing_dates": ["2026-01-02"] if quality_status == "WARN" else [],
                "invalid_ohlc": [{"timestamp": "2026-01-02"}]
                if quality_status == "FAIL"
                else [],
                "volume_warnings": [],
                "quality_error": None,
            },
        ],
        "errors": [
            {
                "symbol": "AAPL",
                "code": "INVALID_OHLC",
                "message": "Invalid OHLC rows were found.",
                "count": 1,
            },
        ]
        if quality_status == "FAIL"
        else [],
        "warnings": [
            {
                "symbol": "AAPL",
                "code": "MISSING_DATES",
                "message": "Missing daily bars were found.",
                "count": 1,
            },
        ]
        if quality_status == "WARN"
        else [],
    }

    def fake_ingest_market_snapshot(
        market,
        start,
        end,
        session,
        provider_name,
    ):
        return {
            "market": market,
            "instrument_count": 1,
            "bar_count": 2,
            "status": "ingested",
            "quality_diagnostics": quality_diagnostics,
        }

    monkeypatch.setattr(ingestion_tasks, "SessionLocal", lambda: session)
    monkeypatch.setattr(
        ingestion_tasks,
        "ingest_market_snapshot",
        fake_ingest_market_snapshot,
    )

    result = ingestion_tasks.ingest_market_data(
        market="US",
        start="2026-01-01",
        end="2026-01-02",
        provider="mock",
    )
    latest_run = get_latest_task_run_payload(
        session=session,
        task_name="ingestion.ingest_market_data",
    )

    assert result == latest_run["result_json"]
    assert result["market"] == "US"
    assert result["instrument_count"] == 1
    assert result["bar_count"] == 2
    assert result["status"] == "ingested"
    assert result["provider"] == "mock"
    assert result["quality_diagnostics"] == quality_diagnostics
    assert latest_run["status"] == "succeeded"


def test_ingest_market_data_persists_fallback_when_quality_diagnostics_are_missing(monkeypatch):
    session = make_session()
    from apps.worker.tasks import ingestion as ingestion_tasks

    def fake_ingest_market_snapshot(
        market,
        start,
        end,
        session,
        provider_name,
    ):
        return {
            "market": market,
            "instrument_count": 1,
            "bar_count": 2,
            "status": "ingested",
        }

    monkeypatch.setattr(ingestion_tasks, "SessionLocal", lambda: session)
    monkeypatch.setattr(
        ingestion_tasks,
        "ingest_market_snapshot",
        fake_ingest_market_snapshot,
    )

    result = ingestion_tasks.ingest_market_data(
        market="US",
        start="2026-01-01",
        end="2026-01-02",
        provider="mock",
    )
    latest_run = get_latest_task_run_payload(
        session=session,
        task_name="ingestion.ingest_market_data",
    )

    assert latest_run["status"] == "succeeded"
    assert result["quality_diagnostics"] == {
        "status": "FAIL",
        "instrument_count": 0,
        "instruments": [],
        "errors": [
            {
                "code": "QUALITY_DIAGNOSTICS_MISSING",
                "message": "Ingestion completed without quality diagnostics.",
            },
        ],
        "warnings": [],
    }
    assert latest_run["result_json"] == result


def test_ingest_mock_market_data_returns_summary(monkeypatch):
    session = make_session()
    from apps.worker.tasks import ingestion as ingestion_tasks

    monkeypatch.setattr(ingestion_tasks, "SessionLocal", lambda: session)

    result = ingest_mock_market_data("US", start="2026-01-01", end="2026-01-03")
    assert result["market"] == "US"
    assert result["instrument_count"] >= 1
    assert result["bar_count"] >= 1


def test_ingest_symbol_daily_bars_task_records_succeeded_task_run(monkeypatch):
    session = make_session()
    from apps.worker.tasks import ingestion as ingestion_tasks

    monkeypatch.setattr(ingestion_tasks, "SessionLocal", lambda: session)

    result = ingestion_tasks.ingest_symbol_daily_bars_task(
        symbol="aapl",
        market="us",
        start="2026-01-01",
        end="2026-01-02",
        provider="mock",
        asset_type="etf",
    )
    latest_run = get_latest_task_run_payload(
        session=session,
        task_name="ingestion.ingest_symbol_daily_bars",
    )

    assert result["status"] == "ingested"
    assert result["symbol"] == "AAPL"
    assert result["market"] == "US"
    assert result["asset_type"] == "etf"
    assert result["provider"] == "mock"
    assert result["bar_count"] == 2
    assert latest_run["status"] == "succeeded"
    assert latest_run["input_json"]["asset_type"] == "etf"
    assert latest_run["result_json"] == result


def test_ingest_symbol_daily_bars_batch_task_records_succeeded_task_run(monkeypatch):
    session = make_session()
    from apps.worker.tasks import ingestion as ingestion_tasks

    monkeypatch.setattr(ingestion_tasks, "SessionLocal", lambda: session)

    result = ingestion_tasks.ingest_symbol_daily_bars_batch_task(
        symbols=["aapl", "msft", "aapl"],
        market="us",
        start="2026-01-01",
        end="2026-01-02",
        provider="mock",
        asset_type="etf",
    )
    latest_run = get_latest_task_run_payload(
        session=session,
        task_name="ingestion.ingest_symbol_daily_bars_batch",
    )

    assert result["status"] == "ingested"
    assert result["symbols"] == ["AAPL", "MSFT"]
    assert result["market"] == "US"
    assert result["asset_type"] == "etf"
    assert result["symbol_count"] == 2
    assert result["succeeded_count"] == 2
    assert result["total_bar_count"] == 4
    assert latest_run["status"] == "succeeded"
    assert latest_run["input_json"]["symbols"] == ["AAPL", "MSFT"]
    assert latest_run["input_json"]["asset_type"] == "etf"
    assert latest_run["result_json"] == result


def test_ingest_symbol_daily_bars_batch_task_records_failed_invalid_symbols(monkeypatch):
    session = make_session()
    from apps.worker.tasks import ingestion as ingestion_tasks

    monkeypatch.setattr(ingestion_tasks, "SessionLocal", lambda: session)

    with pytest.raises(ValueError, match="At least one symbol"):
        ingestion_tasks.ingest_symbol_daily_bars_batch_task(
            symbols=" , ,, ",
            market="us",
            start="2026-01-01",
            end="2026-01-02",
            provider="mock",
        )
    latest_run = get_latest_task_run_payload(
        session=session,
        task_name="ingestion.ingest_symbol_daily_bars_batch",
    )

    assert latest_run["status"] == "failed"
    assert latest_run["input_json"]["symbols"] == []
    assert latest_run["error_message"] == "At least one symbol is required for batch daily bar ingestion."


def test_refresh_daily_stock_analysis_task_stores_latest_daily_report(monkeypatch):
    session = make_session()
    monkeypatch.setattr(report_tasks, "SessionLocal", lambda: session)

    result = report_tasks.refresh_daily_stock_analysis(
        symbol="AAPL",
        market="US",
        start="2026-01-01",
        end="2026-01-20",
        ma_window=3,
        provider="mock",
    )
    latest = get_latest_daily_report_payload("AAPL", session=session)
    latest_run = get_latest_task_run_payload(
        session=session,
        task_name="reports.refresh_daily_stock_analysis",
    )

    assert result["symbol"] == "AAPL"
    assert result["status"] == "refreshed"
    assert result["report"]["status"] == "stored"
    assert latest["as_of"] == date(2026, 1, 20).isoformat()
    assert latest_run["status"] == "succeeded"
    assert result["report"]["task_run_id"] == latest_run["id"]
    assert result["report"]["source_summary"]["provider"] == "mock"
    assert result["report"]["source_summary"]["task_run_id"] == latest_run["id"]
    assert latest["task_run_id"] == latest_run["id"]
    assert latest["source_summary"]["task_run_id"] == latest_run["id"]
    assert "Apple reports strong growth in services revenue" in latest["content_markdown"]


def test_refresh_daily_watchlist_analysis_task_stores_reports_for_each_symbol(monkeypatch):
    session = make_session()
    monkeypatch.setattr(report_tasks, "SessionLocal", lambda: session)

    result = report_tasks.refresh_daily_watchlist_analysis(
        watchlist="AAPL:US,0700:HK",
        start="2026-01-01",
        end="2026-01-20",
        ma_window=3,
        provider="mock",
    )
    aapl_latest = get_latest_daily_report_payload("AAPL", session=session)
    hk_latest = get_latest_daily_report_payload("0700", session=session)
    latest_run = get_latest_task_run_payload(
        session=session,
        task_name="reports.refresh_daily_watchlist_analysis",
    )

    assert result["status"] == "refreshed"
    assert result["item_count"] == 2
    assert [item["symbol"] for item in result["items"]] == ["AAPL", "0700"]
    assert latest_run["status"] == "succeeded"
    assert result["items"][0]["report"]["task_run_id"] == latest_run["id"]
    assert result["items"][1]["report"]["task_run_id"] == latest_run["id"]
    assert result["items"][0]["report"]["source_summary"]["provider"] == "mock"
    assert result["items"][1]["report"]["source_summary"]["provider"] == "mock"
    assert aapl_latest["as_of"] == date(2026, 1, 20).isoformat()
    assert hk_latest["as_of"] == date(2026, 1, 20).isoformat()
    assert aapl_latest["task_run_id"] == latest_run["id"]
    assert hk_latest["task_run_id"] == latest_run["id"]


def test_refresh_daily_watchlist_analysis_task_records_succeeded_run(monkeypatch):
    session = make_session()
    monkeypatch.setattr(report_tasks, "SessionLocal", lambda: session)

    report_tasks.refresh_daily_watchlist_analysis(
        watchlist="AAPL:US",
        start="2026-01-01",
        end="2026-01-20",
        ma_window=3,
        provider="mock",
    )
    latest_run = get_latest_task_run_payload(
        session=session,
        task_name="reports.refresh_daily_watchlist_analysis",
    )

    assert latest_run["status"] == "succeeded"
    assert latest_run["input_json"]["watchlist"] == "AAPL:US"
    assert latest_run["result_json"]["item_count"] == 1


def test_refresh_daily_watchlist_analysis_task_uses_persisted_watchlist(monkeypatch):
    session = make_session()
    monkeypatch.setattr(report_tasks, "SessionLocal", lambda: session)
    upsert_watchlist_item(
        "0700",
        "HK",
        session=session,
        name="Tencent Holdings",
        alert_rules={"price_above": 400},
    )

    result = report_tasks.refresh_daily_watchlist_analysis(
        start="2026-01-01",
        end="2026-01-20",
        ma_window=3,
        provider="mock",
    )
    latest_run = get_latest_task_run_payload(
        session=session,
        task_name="reports.refresh_daily_watchlist_analysis",
    )

    assert result["status"] == "refreshed"
    assert result["item_count"] == 1
    assert result["items"][0]["symbol"] == "0700"
    assert result["items"][0]["market"] == "HK"
    assert latest_run["input_json"]["watchlist"] == "0700:HK"


def test_refresh_daily_watchlist_analysis_task_records_failed_run(monkeypatch):
    session = make_session()
    monkeypatch.setattr(report_tasks, "SessionLocal", lambda: session)

    def fail_refresh(**kwargs):
        raise RuntimeError("provider timeout")

    monkeypatch.setattr(report_tasks, "refresh_stock_analysis", fail_refresh)

    with pytest.raises(RuntimeError, match="provider timeout"):
        report_tasks.refresh_daily_watchlist_analysis(
            watchlist="AAPL:US",
            start="2026-01-01",
            end="2026-01-20",
            ma_window=3,
            provider="mock",
        )
    latest_run = get_latest_task_run_payload(
        session=session,
        task_name="reports.refresh_daily_watchlist_analysis",
    )

    assert latest_run["status"] == "failed"
    assert latest_run["error_message"] == "provider timeout"
    assert latest_run["input_json"]["watchlist"] == "AAPL:US"


def test_refresh_daily_watchlist_analysis_reuses_existing_task_run(monkeypatch):
    session = make_session()
    monkeypatch.setattr(report_tasks, "SessionLocal", lambda: session)
    from packages.services.task_runs import start_task_run

    existing_run = start_task_run(
        "reports.refresh_daily_watchlist_analysis",
        {"watchlist": "AAPL:US", "retry_of": "original-id"},
        session=session,
    )

    result = report_tasks.refresh_daily_watchlist_analysis(
        watchlist="AAPL:US",
        start="2026-01-01",
        end="2026-01-20",
        ma_window=3,
        provider="mock",
        task_run_id=str(existing_run.id),
    )
    latest_run = get_latest_task_run_payload(
        session=session,
        task_name="reports.refresh_daily_watchlist_analysis",
    )

    assert result["status"] == "refreshed"
    assert latest_run["id"] == str(existing_run.id)
    assert latest_run["status"] == "succeeded"
    assert latest_run["result_json"]["item_count"] == 1


def test_evaluate_watchlist_alerts_task_records_trigger_and_task_run(monkeypatch):
    session = make_session()
    from apps.worker.tasks import alerts as alert_tasks

    monkeypatch.setattr(alert_tasks, "SessionLocal", lambda: session)
    upsert_watchlist_item(
        "AAPL",
        "US",
        session=session,
        alert_rules={"price_above": 1},
    )

    def fake_evaluate(session, provider_name=None):
        from packages.services.alert_triggers import record_triggered_alerts

        record_triggered_alerts(
            "AAPL",
            "US",
            {
                "triggered": True,
                "rules": [
                    {"key": "price_above", "threshold": 1, "value": 120, "triggered": True},
                ],
            },
            session=session,
        )
        return {
            "status": "evaluated",
            "provider": provider_name or "mock",
            "item_count": 1,
            "triggered_count": 1,
            "items": [{"symbol": "AAPL", "market": "US", "alert_status": {"triggered": True}}],
        }

    monkeypatch.setattr(alert_tasks, "evaluate_all_watchlist_alerts", fake_evaluate)

    result = alert_tasks.evaluate_watchlist_alerts(provider="mock")
    latest_run = get_latest_task_run_payload(
        session=session,
        task_name="alerts.evaluate_watchlist_alerts",
    )

    assert result["status"] == "evaluated"
    assert result["triggered_count"] == 1
    assert latest_run["status"] == "succeeded"
    assert latest_run["result_json"]["triggered_count"] == 1
