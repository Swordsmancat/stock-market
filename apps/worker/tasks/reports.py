from datetime import date

from apps.worker.celery_app import celery_app
from packages.services.analysis import refresh_stock_analysis
from packages.shared.database import SessionLocal


@celery_app.task(name="reports.generate_daily_reports")
def generate_daily_reports(scope: str) -> dict[str, str]:
    return {"scope": scope, "status": "scheduled"}


@celery_app.task(name="reports.refresh_daily_stock_analysis")
def refresh_daily_stock_analysis(
    symbol: str,
    market: str,
    start: str,
    end: str,
    ma_window: int = 20,
) -> dict[str, object]:
    session = SessionLocal()
    try:
        return refresh_stock_analysis(
            symbol=symbol,
            market=market,
            start=date.fromisoformat(start),
            end=date.fromisoformat(end),
            session=session,
            ma_window=ma_window,
        )
    finally:
        session.close()
