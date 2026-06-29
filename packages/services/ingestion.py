from datetime import date

from packages.services.market_data import get_market_snapshot


def ingest_mock_market_snapshot(market: str, start: date, end: date) -> dict[str, object]:
    snapshot = get_market_snapshot(market, start, end)
    bar_count = sum(len(instrument["bars"]) for instrument in snapshot["instruments"])
    return {
        **snapshot,
        "bar_count": bar_count,
        "status": "ingested",
    }
