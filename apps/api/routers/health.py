from urllib.parse import urlsplit

from fastapi import APIRouter

from apps.worker.celery_app import celery_app
from packages.shared.config import settings

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/runtime")
def runtime_health() -> dict[str, str]:
    """Expose non-secret runtime identity so operators can target isolated stacks safely."""
    database_url = settings.database_url.replace("postgresql+psycopg", "postgresql", 1)
    return {
        "status": "ok",
        "app_env": settings.app_env,
        "database_name": urlsplit(database_url).path.lstrip("/"),
        "celery_timezone": str(celery_app.conf.timezone),
    }
