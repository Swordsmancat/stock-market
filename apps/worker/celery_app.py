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
            "watchlist": settings.daily_report_watchlist,
            "start": settings.daily_report_start,
            "end": settings.daily_report_end,
            "ma_window": settings.daily_report_ma_window,
        },
    }
}
celery_app.autodiscover_tasks(["apps.worker.tasks"])
