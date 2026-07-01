from celery import Celery
from celery.schedules import crontab

from packages.shared.config import settings

celery_app = Celery(
    "stock_analysis_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
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
}
celery_app.autodiscover_tasks(["apps.worker.tasks"])
