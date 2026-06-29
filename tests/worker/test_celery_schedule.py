from apps.worker.celery_app import celery_app


def test_celery_beat_schedules_daily_watchlist_analysis_report():
    schedule = celery_app.conf.beat_schedule["daily-watchlist-analysis-report"]

    assert schedule["task"] == "reports.refresh_daily_watchlist_analysis"
    assert schedule["kwargs"] == {
        "watchlist": "AAPL:US",
        "start": "2026-01-01",
        "end": "2026-01-20",
        "ma_window": 3,
    }
