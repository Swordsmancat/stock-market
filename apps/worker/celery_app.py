from celery import Celery

from packages.shared.config import settings

celery_app = Celery(
    "stock_analysis_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.autodiscover_tasks(["apps.worker.tasks"])
