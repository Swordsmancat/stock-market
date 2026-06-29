from apps.worker.tasks.ingestion import ingest_mock_market_data


def test_ingest_mock_market_data_returns_summary():
    result = ingest_mock_market_data("US")
    assert result["market"] == "US"
    assert result["instrument_count"] >= 1
    assert result["bar_count"] >= 1
