from apps.worker.celery_app import celery_app
from packages.shared.config import settings


def test_celery_uses_explicit_shanghai_timezone():
    assert celery_app.conf.timezone == "Asia/Shanghai"
    assert celery_app.conf.enable_utc is True


def test_celery_beat_schedules_daily_watchlist_analysis_report():
    schedule = celery_app.conf.beat_schedule["daily-watchlist-analysis-report"]

    assert schedule["task"] == "reports.refresh_daily_watchlist_analysis"
    assert schedule["kwargs"] == {"ma_window": 3}


def test_celery_beat_schedules_daily_stock_analysis_report():
    schedule = celery_app.conf.beat_schedule["daily-stock-analysis-report"]

    assert schedule["task"] == "reports.refresh_daily_stock_analysis"
    assert schedule["kwargs"] == {
        "symbol": "AAPL",
        "market": "US",
        "ma_window": 3,
    }


def test_celery_beat_schedules_daily_market_data_ingestion():
    schedule = celery_app.conf.beat_schedule["daily-market-data-ingestion-us"]

    assert schedule["task"] == "ingestion.ingest_market_data"
    assert schedule["kwargs"] == {"market": "US", "provider": "yfinance"}


def test_celery_beat_schedules_hk_and_cn_market_data_ingestion():
    hk = celery_app.conf.beat_schedule["daily-market-data-ingestion-hk"]
    cn = celery_app.conf.beat_schedule["daily-market-data-ingestion-cn"]

    assert hk["kwargs"] == {"market": "HK", "provider": "yfinance"}
    assert cn["kwargs"] == {"market": "CN", "provider": "yfinance"}


def test_celery_beat_schedules_watchlist_alert_evaluation():
    schedule = celery_app.conf.beat_schedule["watchlist-alert-evaluation"]

    assert schedule["task"] == "alerts.evaluate_watchlist_alerts"
    assert schedule["kwargs"] == {"provider": "yfinance"}


def test_celery_beat_schedules_a_share_incremental_evidence_refreshes():
    incremental = celery_app.conf.beat_schedule["daily-a-share-evidence-incremental"]
    fundamentals = celery_app.conf.beat_schedule["daily-a-share-fundamental-shard"]

    assert incremental["task"] == "ingestion.schedule_a_share_evidence_backfill"
    assert incremental["kwargs"] == {
        "run_kind": "incremental",
        "evidence_kinds": ["daily_bars", "technical_indicators"],
    }
    assert fundamentals["task"] == "ingestion.schedule_a_share_evidence_backfill"
    assert fundamentals["kwargs"] == {
        "run_kind": "fundamental_shard",
        "evidence_kinds": ["fundamentals"],
        "shard_count": 5,
    }


def test_celery_beat_schedules_incremental_watchlist_disclosure_monitor():
    schedule = celery_app.conf.beat_schedule["watchlist-official-disclosure-monitor"]

    assert schedule["task"] == "ingestion.schedule_watchlist_official_disclosures"
    assert schedule["kwargs"] == {}
    assert schedule["schedule"].total_seconds() == max(
        15,
        settings.disclosure_monitor_interval_minutes,
    ) * 60
