from datetime import date

from apps.worker.celery_app import celery_app
from packages.services.ingestion import ingest_mock_market_snapshot


@celery_app.task(name="ingestion.ingest_mock_market_data")
def ingest_mock_market_data(market: str) -> dict[str, int | str]:
    snapshot = ingest_mock_market_snapshot(market, date(2026, 1, 1), date(2026, 1, 3))
    return {
        "market": str(snapshot["market"]),
        "instrument_count": int(snapshot["instrument_count"]),
        "bar_count": int(snapshot["bar_count"]),
        "status": str(snapshot["status"]),
    }
