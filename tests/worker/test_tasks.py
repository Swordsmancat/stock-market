from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

import packages.domain.models  # noqa: F401
from apps.worker.tasks.ingestion import ingest_mock_market_data
from apps.worker.tasks import reports as report_tasks
from packages.services.reports import get_latest_daily_report_payload
from packages.services.task_runs import get_latest_task_run_payload, start_task_run
from packages.services.watchlists import remove_watchlist_item, upsert_watchlist_item
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


def test_eastmoney_calendar_task_records_progress_and_success(monkeypatch):
    session = make_session()
    from apps.worker.tasks import ingestion as ingestion_tasks

    monkeypatch.setattr(ingestion_tasks, "SessionLocal", lambda: session)

    def fake_refresh(*, session, progress_callback, **_kwargs):
        progress_callback("persisted", 1, 1, "Calendar refresh persisted.")
        return {
            "status": "ok",
            "provider": "eastmoney_public",
            "pipeline": "economic_calendar",
            "stored_count": 3,
        }

    monkeypatch.setattr(ingestion_tasks, "refresh_eastmoney_calendar_batch", fake_refresh)

    result = ingestion_tasks.refresh_eastmoney_economic_calendar_task()
    latest_run = get_latest_task_run_payload(
        session=session,
        task_name="ingestion.refresh_eastmoney_economic_calendar",
    )

    assert result["stored_count"] == 3
    assert latest_run["status"] == "succeeded"
    assert latest_run["result_json"] == result


def test_eastmoney_task_skips_fresh_overlap_without_provider_call(monkeypatch):
    session = make_session()
    from apps.worker.tasks import ingestion as ingestion_tasks

    monkeypatch.setattr(ingestion_tasks, "SessionLocal", lambda: session)
    start_task_run(
        "ingestion.refresh_eastmoney_economic_calendar",
        {"pipeline": "economic_calendar"},
        session=session,
    )
    called = False

    def fake_refresh(**_kwargs):
        nonlocal called
        called = True
        return {"status": "ok"}

    monkeypatch.setattr(ingestion_tasks, "refresh_eastmoney_calendar_batch", fake_refresh)

    result = ingestion_tasks.refresh_eastmoney_economic_calendar_task()

    assert result["status"] == "skipped"
    assert result["code"] == "ALREADY_RUNNING"
    assert called is False


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


def test_cn_fund_index_pipeline_task_records_progress_and_success(monkeypatch):
    session = make_session()
    from apps.worker.tasks import ingestion as ingestion_tasks

    monkeypatch.setattr(ingestion_tasks, "SessionLocal", lambda: session)

    def fake_sync(*, progress_callback, **_kwargs):
        progress_callback("daily_bars", 2, 2, "Completed.")
        return {
            "status": "ok",
            "provider": "akshare",
            "pipeline": "cn_fund_index_data",
            "assets": {
                "etf": {"catalog_count": 1, "bar_count": 2},
                "index": {"catalog_count": 1, "bar_count": 2},
            },
        }

    monkeypatch.setattr(ingestion_tasks, "sync_cn_fund_index_data", fake_sync)

    result = ingestion_tasks.sync_cn_fund_index_data_task(
        lookback_days=30,
        max_symbols_per_type=10,
    )
    latest_run = get_latest_task_run_payload(
        session=session,
        task_name="ingestion.sync_cn_fund_index_data",
    )

    assert result["status"] == "ok"
    assert latest_run["status"] == "succeeded"
    assert latest_run["input_json"]["asset_types"] == ["etf", "index"]


def test_cn_fund_index_pipeline_task_skips_fresh_overlap(monkeypatch):
    session = make_session()
    from apps.worker.tasks import ingestion as ingestion_tasks

    monkeypatch.setattr(ingestion_tasks, "SessionLocal", lambda: session)
    start_task_run(
        "ingestion.sync_cn_fund_index_data",
        {"pipeline": "cn_fund_index_data"},
        session=session,
    )
    monkeypatch.setattr(
        ingestion_tasks,
        "sync_cn_fund_index_data",
        lambda **_kwargs: pytest.fail("overlap must not call provider pipeline"),
    )

    result = ingestion_tasks.sync_cn_fund_index_data_task()

    assert result["status"] == "skipped"
    assert result["code"] == "ALREADY_RUNNING"


@pytest.mark.parametrize(
    ("task_kwargs", "expected_policy"),
    [
        ({"daily_bar_policy": "cn_resilient"}, "cn_resilient"),
        ({}, "strict"),
    ],
)
def test_scheduled_a_share_backfill_forwards_daily_bar_policy(
    monkeypatch,
    task_kwargs,
    expected_policy,
):
    session = make_session()
    from apps.worker.tasks import ingestion as ingestion_tasks

    captured = {}

    def fake_create_backfill_run(request, *, session):
        captured["request"] = request
        return {"status": "already_running"}

    monkeypatch.setattr(ingestion_tasks, "SessionLocal", lambda: session)
    monkeypatch.setattr(
        ingestion_tasks,
        "create_backfill_run",
        fake_create_backfill_run,
    )

    result = ingestion_tasks.schedule_a_share_evidence_backfill_task(
        run_kind="incremental",
        evidence_kinds=["daily_bars", "technical_indicators"],
        **task_kwargs,
    )

    assert result == {"status": "already_running"}
    assert captured["request"].daily_bar_policy == expected_policy


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


def test_watchlist_official_disclosures_task_records_progress_and_success(monkeypatch):
    session = make_session()
    from apps.worker.tasks import ingestion as ingestion_tasks

    monkeypatch.setattr(ingestion_tasks, "SessionLocal", lambda: session)

    def fake_ingest(*, session, lookback_days, max_documents, request_delay_seconds, progress_callback):
        assert lookback_days == 45
        assert max_documents == 12
        assert request_delay_seconds >= 0.25
        progress_callback("metadata", 1, 2, "Metadata complete.")
        progress_callback("documents", 2, 2, "Documents complete.")
        return {"status": "ok", "summary": {"processed_document_count": 1}}

    monkeypatch.setattr(ingestion_tasks, "ingest_watchlist_official_disclosures", fake_ingest)

    result = ingestion_tasks.ingest_watchlist_official_disclosures_task(
        lookback_days=45,
        max_documents=12,
    )
    latest_run = get_latest_task_run_payload(
        session=session,
        task_name="ingestion.ingest_watchlist_official_disclosures",
    )

    assert result["status"] == "ok"
    assert latest_run["status"] == "succeeded"
    assert latest_run["result_json"] == result


def test_scheduled_watchlist_disclosure_monitor_enqueues_incremental_mode(monkeypatch):
    session = make_session()
    from apps.worker.tasks import ingestion as ingestion_tasks

    monkeypatch.setattr(ingestion_tasks, "SessionLocal", lambda: session)
    captured = {}

    def fake_enqueue(*, session, lookback_days, max_documents, mode):
        captured.update(
            lookback_days=lookback_days,
            max_documents=max_documents,
            mode=mode,
        )
        return {"status": "dispatched", "task_run": {"id": "task-monitor"}}

    monkeypatch.setattr(
        ingestion_tasks,
        "enqueue_watchlist_official_disclosure_ingestion",
        fake_enqueue,
    )

    result = ingestion_tasks.schedule_watchlist_official_disclosures_task()

    assert result["status"] == "dispatched"
    assert captured == {
        "lookback_days": ingestion_tasks.settings.disclosure_monitor_lookback_days,
        "max_documents": ingestion_tasks.settings.disclosure_monitor_max_documents,
        "mode": "incremental",
    }


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


def test_refresh_daily_watchlist_analysis_skips_intentionally_empty_watchlist(monkeypatch):
    session = make_session()
    monkeypatch.setattr(report_tasks, "SessionLocal", lambda: session)
    upsert_watchlist_item("AAPL", "US", session=session, name="Apple Inc.")
    remove_watchlist_item("AAPL", "US", session=session)

    def fail_if_called(**_kwargs):
        raise AssertionError("empty watchlist must not refresh stock analysis")

    monkeypatch.setattr(report_tasks, "refresh_stock_analysis", fail_if_called)

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

    assert result == {
        "status": "skipped",
        "reason": "empty_watchlist",
        "item_count": 0,
        "items": [],
    }
    assert latest_run["status"] == "succeeded"
    assert latest_run["input_json"]["watchlist"] == ""
    assert latest_run["result_json"] == result


def test_refresh_daily_watchlist_analysis_reuses_task_run_for_explicit_empty_watchlist(monkeypatch):
    session = make_session()
    monkeypatch.setattr(report_tasks, "SessionLocal", lambda: session)
    from packages.services.task_runs import start_task_run

    existing_run = start_task_run(
        "reports.refresh_daily_watchlist_analysis",
        {"watchlist": "", "retry_of": "original-id"},
        session=session,
    )

    def fail_if_called(**_kwargs):
        raise AssertionError("empty watchlist must not refresh stock analysis")

    monkeypatch.setattr(report_tasks, "refresh_stock_analysis", fail_if_called)

    result = report_tasks.refresh_daily_watchlist_analysis(
        watchlist="",
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

    assert result["status"] == "skipped"
    assert result["reason"] == "empty_watchlist"
    assert latest_run["id"] == str(existing_run.id)
    assert latest_run["status"] == "succeeded"
    assert latest_run["input_json"] == {"watchlist": "", "retry_of": "original-id"}
    assert session.query(packages.domain.models.TaskRun).count() == 1


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


def test_evaluate_watchlist_alerts_task_skips_no_rule_beat_delivery_without_task_run(monkeypatch):
    session = make_session()
    from apps.worker.tasks import alerts as alert_tasks

    monkeypatch.setattr(alert_tasks, "SessionLocal", lambda: session)
    close_calls = 0
    original_close = session.close

    def track_close():
        nonlocal close_calls
        close_calls += 1
        original_close()

    def fail_if_called(**_kwargs):
        raise AssertionError("no-rule delivery must not evaluate alerts")

    monkeypatch.setattr(session, "close", track_close)
    monkeypatch.setattr(alert_tasks, "evaluate_all_watchlist_alerts", fail_if_called)

    result = alert_tasks.evaluate_watchlist_alerts(provider="mock")

    assert result == {
        "status": "skipped",
        "reason": "no_alert_rules",
        "item_count": 0,
        "triggered_count": 0,
        "items": [],
    }
    assert session.query(packages.domain.models.TaskRun).count() == 0
    assert session.query(packages.domain.models.AlertTrigger).count() == 0
    assert close_calls == 1


def test_evaluate_watchlist_alerts_task_skips_soft_removed_watchlist_without_task_run(monkeypatch):
    session = make_session()
    from apps.worker.tasks import alerts as alert_tasks

    monkeypatch.setattr(alert_tasks, "SessionLocal", lambda: session)
    upsert_watchlist_item(
        "AAPL",
        "US",
        session=session,
        alert_rules={"price_above": 1},
    )
    remove_watchlist_item("AAPL", "US", session=session)

    result = alert_tasks.evaluate_watchlist_alerts(provider="mock")

    assert result["status"] == "skipped"
    assert result["reason"] == "no_alert_rules"
    assert session.query(packages.domain.models.TaskRun).count() == 0
    assert session.query(packages.domain.models.AlertTrigger).count() == 0


def test_evaluate_watchlist_alerts_task_reuses_supplied_no_rule_task_run(monkeypatch):
    session = make_session()
    from apps.worker.tasks import alerts as alert_tasks
    from packages.services.task_runs import start_task_run

    monkeypatch.setattr(alert_tasks, "SessionLocal", lambda: session)
    existing_run = start_task_run(
        "alerts.evaluate_watchlist_alerts",
        {"provider": "mock", "retry_of": "original-id"},
        session=session,
    )

    result = alert_tasks.evaluate_watchlist_alerts(
        provider="mock",
        task_run_id=str(existing_run.id),
    )
    latest_run = get_latest_task_run_payload(
        session=session,
        task_name="alerts.evaluate_watchlist_alerts",
    )

    assert result["status"] == "skipped"
    assert result["reason"] == "no_alert_rules"
    assert latest_run["id"] == str(existing_run.id)
    assert latest_run["status"] == "succeeded"
    assert latest_run["input_json"]["retry_of"] == "original-id"
    assert latest_run["result_json"] == result
    assert session.query(packages.domain.models.TaskRun).count() == 1


def test_evaluate_watchlist_alerts_task_records_preflight_database_failure(monkeypatch):
    session = make_session()
    from apps.worker.tasks import alerts as alert_tasks
    from packages.services import watchlists as watchlist_service

    monkeypatch.setattr(alert_tasks, "SessionLocal", lambda: session)
    rollback_calls = 0
    close_calls = 0
    original_rollback = session.rollback
    original_close = session.close

    def track_rollback():
        nonlocal rollback_calls
        rollback_calls += 1
        original_rollback()

    def track_close():
        nonlocal close_calls
        close_calls += 1
        original_close()

    monkeypatch.setattr(session, "rollback", track_rollback)
    monkeypatch.setattr(session, "close", track_close)

    def fail_active_items(_session):
        raise SQLAlchemyError("watchlist unavailable")

    monkeypatch.setattr(watchlist_service, "get_active_watchlist_item_dicts", fail_active_items)

    with pytest.raises(SQLAlchemyError, match="watchlist unavailable"):
        alert_tasks.evaluate_watchlist_alerts(provider="mock")

    latest_run = get_latest_task_run_payload(
        session=session,
        task_name="alerts.evaluate_watchlist_alerts",
    )
    assert latest_run["status"] == "failed"
    assert latest_run["error_message"] == "watchlist unavailable"
    assert session.query(packages.domain.models.TaskRun).count() == 1
    assert rollback_calls == 1
    assert close_calls == 1


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
    assert session.query(packages.domain.models.TaskRun).count() == 1
    assert session.query(packages.domain.models.AlertTrigger).count() == 1
