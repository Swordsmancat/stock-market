from datetime import timedelta

from celery import Celery
from celery.schedules import crontab

from packages.services.daily_bar_sources import CN_RESILIENT_POLICY
from packages.shared.config import settings


def _eastmoney_automation_schedule() -> dict[str, dict[str, object]]:
    if not settings.eastmoney_automation_enabled:
        return {}
    return {
        "eastmoney-economic-calendar": {
            "task": "ingestion.refresh_eastmoney_economic_calendar",
            "schedule": crontab(
                hour=settings.eastmoney_calendar_cron_hour,
                minute=settings.eastmoney_calendar_cron_minute,
            ),
            "kwargs": {"trigger": "scheduled"},
        },
        "eastmoney-industry-rankings": {
            "task": "ingestion.refresh_eastmoney_industry_rankings",
            "schedule": crontab(
                hour=settings.eastmoney_industry_cron_hour,
                minute=settings.eastmoney_industry_cron_minute,
                day_of_week="1-5",
            ),
            "kwargs": {"trigger": "scheduled"},
        },
        "eastmoney-research-news": {
            "task": "ingestion.refresh_eastmoney_research_news",
            "schedule": timedelta(
                minutes=max(15, settings.eastmoney_news_interval_minutes)
            ),
            "kwargs": {"trigger": "scheduled"},
        },
        "eastmoney-research-fundamentals": {
            "task": "ingestion.refresh_eastmoney_research_fundamentals",
            "schedule": crontab(
                hour=settings.eastmoney_fundamentals_cron_hour,
                minute=settings.eastmoney_fundamentals_cron_minute,
                day_of_week="1-5",
            ),
            "kwargs": {"trigger": "scheduled"},
        },
    }


def _daily_research_loop_schedule() -> dict[str, dict[str, object]]:
    if not settings.daily_research_loop_enabled:
        return {}
    return {
        "daily-a-share-research-loop": {
            "task": "research.run_daily_research_loop",
            "schedule": crontab(
                hour=settings.daily_research_loop_cron_hour,
                minute=settings.daily_research_loop_cron_minute,
                day_of_week="1-5",
            ),
            "kwargs": {
                "market": "CN",
                "asset_type": "stock",
                "profile_id": "balanced_research",
                "shortlist_limit": 10,
                "locale": "zh",
                "use_llm": True,
                "outcome_run_limit": settings.daily_research_loop_outcome_run_limit,
                "trigger": "scheduled",
            },
        }
    }


def _cn_fund_index_schedule() -> dict[str, dict[str, object]]:
    if not settings.cn_fund_index_pipeline_enabled:
        return {}
    return {
        "daily-cn-etf-index-ingestion": {
            "task": "ingestion.sync_cn_fund_index_data",
            "schedule": crontab(
                hour=settings.cn_fund_index_pipeline_cron_hour,
                minute=settings.cn_fund_index_pipeline_cron_minute,
                day_of_week="1-5",
            ),
            "kwargs": {
                "lookback_days": settings.cn_fund_index_pipeline_lookback_days,
                "max_symbols_per_type": (
                    settings.cn_fund_index_pipeline_max_symbols_per_type
                ),
                "trigger": "scheduled",
            },
        }
    }


celery_app = Celery(
    "stock_analysis_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.timezone = "Asia/Shanghai"
celery_app.conf.enable_utc = True
celery_app.conf.beat_schedule = {
    "daily-watchlist-analysis-report": {
        "task": "reports.refresh_daily_watchlist_analysis",
        "schedule": crontab(
            hour=settings.daily_report_cron_hour,
            minute=settings.daily_report_cron_minute,
        ),
        "kwargs": {
            "ma_window": settings.daily_report_ma_window,
        },
    },
    "daily-stock-analysis-report": {
        "task": "reports.refresh_daily_stock_analysis",
        "schedule": crontab(
            hour=settings.daily_report_cron_hour,
            minute=(settings.daily_report_cron_minute + 15) % 60,
        ),
        "kwargs": {
            "symbol": settings.daily_report_symbol,
            "market": settings.daily_report_market,
            "ma_window": settings.daily_report_ma_window,
        },
    },
    "daily-market-data-ingestion-us": {
        "task": "ingestion.ingest_market_data",
        "schedule": crontab(hour=6, minute=0),
        "kwargs": {
            "market": "US",
            "provider": settings.market_data_provider,
        },
    },
    "daily-market-data-ingestion-hk": {
        "task": "ingestion.ingest_market_data",
        "schedule": crontab(hour=8, minute=30),
        "kwargs": {
            "market": "HK",
            "provider": settings.market_data_provider,
        },
    },
    "daily-market-data-ingestion-cn": {
        "task": "ingestion.ingest_market_data",
        "schedule": crontab(hour=7, minute=0),
        "kwargs": {
            "market": "CN",
            "provider": settings.market_data_provider,
        },
    },
    "daily-a-share-instrument-universe-sync": {
        "task": "ingestion.sync_instrument_universe",
        "schedule": crontab(hour=6, minute=30),
        "kwargs": {
            "market": "CN",
            "provider": "akshare",
        },
    },
    "daily-a-share-evidence-incremental": {
        "task": "ingestion.schedule_a_share_evidence_backfill",
        "schedule": crontab(hour=18, minute=30, day_of_week="1-5"),
        "kwargs": {
            "run_kind": "incremental",
            "evidence_kinds": ["daily_bars", "technical_indicators"],
            "daily_bar_policy": CN_RESILIENT_POLICY,
        },
    },
    "daily-a-share-fundamental-shard": {
        "task": "ingestion.schedule_a_share_evidence_backfill",
        "schedule": crontab(hour=20, minute=30, day_of_week="1-5"),
        "kwargs": {
            "run_kind": "fundamental_shard",
            "evidence_kinds": ["fundamentals"],
            "shard_count": 5,
        },
    },
    "watchlist-alert-evaluation": {
        "task": "alerts.evaluate_watchlist_alerts",
        "schedule": crontab(minute="*/15"),
        "kwargs": {
            "provider": settings.market_data_provider,
        },
    },
}

if settings.disclosure_monitor_enabled:
    celery_app.conf.beat_schedule["watchlist-official-disclosure-monitor"] = {
        "task": "ingestion.schedule_watchlist_official_disclosures",
        "schedule": timedelta(
            minutes=max(15, settings.disclosure_monitor_interval_minutes),
        ),
        "kwargs": {},
    }

celery_app.conf.beat_schedule.update(_daily_research_loop_schedule())
celery_app.conf.beat_schedule.update(_cn_fund_index_schedule())
celery_app.conf.beat_schedule.update(_eastmoney_automation_schedule())
celery_app.autodiscover_tasks(["apps.worker.tasks"], force=True)

# Manually import tasks to ensure they are registered
from apps.worker.tasks import alerts, indicators, ingestion, reports, research  # noqa: E402, F401
