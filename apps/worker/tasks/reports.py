from apps.worker.celery_app import celery_app


@celery_app.task(name="reports.generate_daily_reports")
def generate_daily_reports(scope: str) -> dict[str, str]:
    return {"scope": scope, "status": "scheduled"}
