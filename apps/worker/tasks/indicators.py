from apps.worker.celery_app import celery_app


@celery_app.task(name="indicators.calculate_daily_indicators")
def calculate_daily_indicators(market: str) -> dict[str, str]:
    return {"market": market, "status": "scheduled"}
