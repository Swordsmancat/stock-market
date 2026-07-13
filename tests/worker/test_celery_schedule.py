from apps.worker.celery_app import _daily_research_loop_schedule, celery_app
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


def test_celery_beat_schedules_daily_a_share_research_loop():
    schedule = celery_app.conf.beat_schedule["daily-a-share-research-loop"]

    assert schedule["task"] == "research.run_daily_research_loop"
    assert schedule["schedule"]._orig_hour == settings.daily_research_loop_cron_hour
    assert schedule["schedule"]._orig_minute == settings.daily_research_loop_cron_minute
    assert schedule["schedule"]._orig_day_of_week == "1-5"
    assert schedule["kwargs"] == {
        "market": "CN",
        "asset_type": "stock",
        "profile_id": "balanced_research",
        "shortlist_limit": 10,
        "locale": "zh",
        "use_llm": True,
        "outcome_run_limit": settings.daily_research_loop_outcome_run_limit,
        "trigger": "scheduled",
    }


def test_daily_research_loop_schedule_honors_custom_settings(monkeypatch):
    monkeypatch.setattr(settings, "daily_research_loop_enabled", True)
    monkeypatch.setattr(settings, "daily_research_loop_cron_hour", 22)
    monkeypatch.setattr(settings, "daily_research_loop_cron_minute", 17)
    monkeypatch.setattr(settings, "daily_research_loop_outcome_run_limit", 42)

    schedule = _daily_research_loop_schedule()["daily-a-share-research-loop"]

    assert schedule["schedule"]._orig_hour == 22
    assert schedule["schedule"]._orig_minute == 17
    assert schedule["schedule"]._orig_day_of_week == "1-5"
    assert schedule["kwargs"]["outcome_run_limit"] == 42


def test_daily_research_loop_schedule_can_be_disabled(monkeypatch):
    monkeypatch.setattr(settings, "daily_research_loop_enabled", False)

    assert _daily_research_loop_schedule() == {}


def test_daily_research_loop_task_is_registered():
    assert "research.run_daily_research_loop" in celery_app.tasks
    assert (
        celery_app.tasks["research.run_daily_research_loop"].name
        == "research.run_daily_research_loop"
    )
