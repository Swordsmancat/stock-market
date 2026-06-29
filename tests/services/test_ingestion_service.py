from datetime import date

from packages.services.ingestion import ingest_mock_market_snapshot


def test_ingest_mock_market_snapshot_returns_serialized_snapshot():
    snapshot = ingest_mock_market_snapshot("US", date(2026, 1, 1), date(2026, 1, 2))

    assert snapshot["market"] == "US"
    assert snapshot["instrument_count"] == 1
    assert snapshot["bar_count"] == 2
    assert snapshot["instruments"][0]["symbol"] == "AAPL"
    assert snapshot["instruments"][0]["bars"][0]["close"] == 101.0
