from apps.worker.celery_app import celery_app


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
