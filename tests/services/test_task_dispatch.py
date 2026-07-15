from unittest.mock import MagicMock, patch

from packages.services.task_dispatch import dispatch_task_run, is_dispatchable_task


def test_is_dispatchable_task_supports_registered_tasks():
    assert is_dispatchable_task("reports.refresh_daily_watchlist_analysis") is True
    assert is_dispatchable_task("reports.refresh_daily_stock_analysis") is True
    assert is_dispatchable_task("ingestion.ingest_market_data") is True
    assert is_dispatchable_task("ingestion.sync_instrument_universe") is True
    assert is_dispatchable_task("ingestion.sync_corporate_actions") is True
    assert is_dispatchable_task("ingestion.ingest_symbol_daily_bars") is True
    assert is_dispatchable_task("ingestion.ingest_symbol_daily_bars_batch") is True
    assert is_dispatchable_task("ingestion.ingest_watchlist_official_disclosures") is True
    assert is_dispatchable_task("research.run_daily_research_loop") is True
    assert is_dispatchable_task("alerts.evaluate_watchlist_alerts") is True
    assert is_dispatchable_task("unknown.task") is False


@patch("apps.worker.tasks.reports.refresh_daily_watchlist_analysis")
def test_dispatch_task_run_enqueues_watchlist_analysis(mock_task):
    mock_result = MagicMock()
    mock_result.id = "celery-id-abc"
    mock_task.delay.return_value = mock_result

    celery_id = dispatch_task_run(
        "reports.refresh_daily_watchlist_analysis",
        {"watchlist": "AAPL:US", "start": "2026-01-01", "end": "2026-01-20", "ma_window": 3},
        "task-run-id",
    )

    assert celery_id == "celery-id-abc"
    mock_task.delay.assert_called_once_with(
        watchlist="AAPL:US",
        start="2026-01-01",
        end="2026-01-20",
        ma_window=3,
        provider=None,
        task_run_id="task-run-id",
    )


@patch("apps.worker.tasks.reports.refresh_daily_stock_analysis")
def test_dispatch_task_run_enqueues_stock_analysis(mock_task):
    mock_result = MagicMock()
    mock_result.id = "celery-id-stock"
    mock_task.delay.return_value = mock_result

    celery_id = dispatch_task_run(
        "reports.refresh_daily_stock_analysis",
        {
            "symbol": "AAPL",
            "market": "US",
            "start": "2026-01-01",
            "end": "2026-01-20",
            "ma_window": 3,
            "provider": "mock",
        },
        "task-run-id",
    )

    assert celery_id == "celery-id-stock"
    mock_task.delay.assert_called_once_with(
        symbol="AAPL",
        market="US",
        start="2026-01-01",
        end="2026-01-20",
        ma_window=3,
        provider="mock",
        task_run_id="task-run-id",
    )


@patch("apps.worker.tasks.alerts.evaluate_watchlist_alerts")
def test_dispatch_task_run_enqueues_alert_evaluation_with_task_run_id(mock_task):
    mock_task.delay.return_value.id = "celery-id-alerts"

    celery_id = dispatch_task_run(
        "alerts.evaluate_watchlist_alerts",
        {"provider": "mock", "retry_of": "original-task-run"},
        "task-run-id",
    )

    assert celery_id == "celery-id-alerts"
    mock_task.delay.assert_called_once_with(
        provider="mock",
        task_run_id="task-run-id",
    )


@patch("apps.worker.tasks.ingestion.ingest_market_data")
def test_dispatch_task_run_enqueues_market_ingestion(mock_task):
    mock_result = MagicMock()
    mock_result.id = "celery-id-ingest"
    mock_task.delay.return_value = mock_result

    celery_id = dispatch_task_run(
        "ingestion.ingest_market_data",
        {
            "market": "US",
            "start": "2026-01-01",
            "end": "2026-01-02",
            "provider": "yfinance",
        },
        "task-run-id",
    )

    assert celery_id == "celery-id-ingest"
    mock_task.delay.assert_called_once_with(
        market="US",
        start="2026-01-01",
        end="2026-01-02",
        provider="yfinance",
        task_run_id="task-run-id",
    )


@patch("apps.worker.tasks.ingestion.sync_instrument_universe_task")
def test_dispatch_task_run_enqueues_instrument_universe_sync(mock_task):
    mock_result = MagicMock()
    mock_result.id = "celery-id-universe"
    mock_task.delay.return_value = mock_result

    celery_id = dispatch_task_run(
        "ingestion.sync_instrument_universe",
        {"market": "CN", "provider": "akshare"},
        "task-run-id",
    )

    assert celery_id == "celery-id-universe"
    mock_task.delay.assert_called_once_with(
        market="CN",
        provider="akshare",
        task_run_id="task-run-id",
    )


@patch("apps.worker.tasks.ingestion.sync_corporate_actions_task")
def test_dispatch_task_run_enqueues_corporate_action_sync(mock_task):
    mock_result = MagicMock()
    mock_result.id = "celery-id-corporate-actions"
    mock_task.delay.return_value = mock_result

    celery_id = dispatch_task_run(
        "ingestion.sync_corporate_actions",
        {
            "report_period": "2025-12-31",
            "market": "CN",
            "provider": "akshare",
            "symbols": ["600519"],
            "event_types": ["dividend_bonus", "rights_allotment"],
            "cursor": 0,
            "batch_size": 50,
        },
        "task-run-id",
    )

    assert celery_id == "celery-id-corporate-actions"
    mock_task.delay.assert_called_once_with(
        report_period="2025-12-31",
        market="CN",
        provider="akshare",
        symbols=["600519"],
        event_types=["dividend_bonus", "rights_allotment"],
        cursor=0,
        batch_size=50,
        task_run_id="task-run-id",
    )


@patch("apps.worker.tasks.ingestion.ingest_symbol_daily_bars_task")
def test_dispatch_task_run_enqueues_symbol_daily_bars_with_asset_type(mock_task):
    mock_result = MagicMock()
    mock_result.id = "celery-id-symbol-bars"
    mock_task.delay.return_value = mock_result

    celery_id = dispatch_task_run(
        "ingestion.ingest_symbol_daily_bars",
        {
            "symbol": "SPY",
            "market": "US",
            "start": "2026-01-01",
            "end": "2026-01-02",
            "provider": "mock",
            "exchange": "NYSE",
            "timeframe": "1d",
            "asset_type": "etf",
        },
        "task-run-id",
    )

    assert celery_id == "celery-id-symbol-bars"
    mock_task.delay.assert_called_once_with(
        symbol="SPY",
        market="US",
        start="2026-01-01",
        end="2026-01-02",
        provider="mock",
        exchange="NYSE",
        timeframe="1d",
        asset_type="etf",
        task_run_id="task-run-id",
    )


@patch("apps.worker.tasks.ingestion.ingest_symbol_daily_bars_batch_task")
def test_dispatch_task_run_enqueues_symbol_daily_bars_batch(mock_task):
    mock_result = MagicMock()
    mock_result.id = "celery-id-symbol-bars-batch"
    mock_task.delay.return_value = mock_result

    celery_id = dispatch_task_run(
        "ingestion.ingest_symbol_daily_bars_batch",
        {
            "symbols": ["AAPL", "MSFT"],
            "market": "US",
            "start": "2026-01-01",
            "end": "2026-01-02",
            "provider": "mock",
            "exchange": "NASDAQ",
            "timeframe": "1d",
            "asset_type": "etf",
        },
        "task-run-id",
    )

    assert celery_id == "celery-id-symbol-bars-batch"
    mock_task.delay.assert_called_once_with(
        symbols=["AAPL", "MSFT"],
        market="US",
        start="2026-01-01",
        end="2026-01-02",
        provider="mock",
        exchange="NASDAQ",
        timeframe="1d",
        asset_type="etf",
        task_run_id="task-run-id",
    )


@patch("apps.worker.tasks.ingestion.backfill_a_share_research_evidence_task")
def test_dispatch_task_run_enqueues_research_evidence_backfill(mock_task):
    mock_result = MagicMock()
    mock_result.id = "celery-id-evidence-backfill"
    mock_task.delay.return_value = mock_result

    celery_id = dispatch_task_run(
        "ingestion.backfill_a_share_research_evidence",
        {
            "backfill_run_id": "backfill-run-id",
            "market": "CN",
            "provider": "akshare",
            "run_kind": "baseline",
        },
        "task-run-id",
    )

    assert celery_id == "celery-id-evidence-backfill"
    mock_task.delay.assert_called_once_with(
        backfill_run_id="backfill-run-id",
        task_run_id="task-run-id",
    )


@patch("apps.worker.tasks.ingestion.ingest_watchlist_official_disclosures_task")
def test_dispatch_task_run_enqueues_watchlist_official_disclosures(mock_task):
    mock_result = MagicMock()
    mock_result.id = "celery-id-disclosures"
    mock_task.delay.return_value = mock_result

    celery_id = dispatch_task_run(
        "ingestion.ingest_watchlist_official_disclosures",
        {"lookback_days": 45, "max_documents": 12},
        "task-run-id",
    )

    assert celery_id == "celery-id-disclosures"
    mock_task.delay.assert_called_once_with(
        lookback_days=45,
        max_documents=12,
        task_run_id="task-run-id",
    )


@patch("apps.worker.tasks.ingestion.ingest_watchlist_official_disclosures_task")
def test_dispatch_task_run_preserves_incremental_disclosure_mode(mock_task):
    mock_task.delay.return_value.id = "celery-id-monitor"

    celery_id = dispatch_task_run(
        "ingestion.ingest_watchlist_official_disclosures",
        {"lookback_days": 30, "max_documents": 20, "mode": "incremental"},
        "task-run-id",
    )

    assert celery_id == "celery-id-monitor"
    mock_task.delay.assert_called_once_with(
        lookback_days=30,
        max_documents=20,
        mode="incremental",
        task_run_id="task-run-id",
    )


@patch("apps.worker.tasks.research.run_daily_research_loop_task")
def test_dispatch_task_run_enqueues_daily_research_loop(mock_task):
    mock_task.delay.return_value.id = "celery-id-daily-research"

    celery_id = dispatch_task_run(
        "research.run_daily_research_loop",
        {
            "market": "CN",
            "asset_type": "stock",
            "profile_id": "balanced_research",
            "shortlist_limit": 8,
            "locale": "zh",
            "use_llm": False,
            "outcome_run_limit": 12,
            "trigger": "scheduled",
            "retry_of": "original-task-run",
        },
        "task-run-id",
    )

    assert celery_id == "celery-id-daily-research"
    mock_task.delay.assert_called_once_with(
        market="CN",
        asset_type="stock",
        profile_id="balanced_research",
        shortlist_limit=8,
        locale="zh",
        use_llm=False,
        outcome_run_limit=12,
        trigger="scheduled",
        task_run_id="task-run-id",
    )
