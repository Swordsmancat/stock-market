from datetime import date

from packages.services import ingestion as ingestion_service
from packages.services.ingestion import ingest_market_snapshot, ingest_mock_market_snapshot


def test_ingest_market_snapshot_returns_serialized_snapshot():
    snapshot = ingest_market_snapshot(
        "US",
        date(2026, 1, 1),
        date(2026, 1, 2),
        provider_name="mock",
    )

    assert snapshot["market"] == "US"
    assert snapshot["provider"] == "mock"
    assert snapshot["instrument_count"] == 1
    assert snapshot["bar_count"] == 2
    assert snapshot["instruments"][0]["symbol"] == "AAPL"
    assert snapshot["instruments"][0]["bars"][0]["close"] == 101.0


def test_ingest_market_snapshot_includes_quality_diagnostics():
    snapshot = ingest_market_snapshot(
        "US",
        date(2026, 1, 1),
        date(2026, 1, 2),
        provider_name="mock",
    )

    quality_diagnostics = snapshot["quality_diagnostics"]
    instrument_diagnostics = quality_diagnostics["instruments"][0]

    assert quality_diagnostics["status"] == "OK"
    assert quality_diagnostics["instrument_count"] == 1
    assert instrument_diagnostics["symbol"] == "AAPL"
    assert instrument_diagnostics["status"] == "OK"
    assert instrument_diagnostics["checked_bars"] == 2
    assert instrument_diagnostics["missing_dates"] == []
    assert instrument_diagnostics["invalid_ohlc"] == []
    assert instrument_diagnostics["volume_warnings"] == []


def test_ingest_market_snapshot_reports_failed_quality_when_no_instruments(monkeypatch):
    def get_empty_market_snapshot(market, start, end, provider_name="mock"):
        return {
            "market": market,
            "provider": provider_name,
            "timeframe": "1d",
            "start": start.isoformat(),
            "end": end.isoformat(),
            "instrument_count": 0,
            "instruments": [],
        }

    monkeypatch.setattr(ingestion_service, "get_market_snapshot", get_empty_market_snapshot)

    snapshot = ingestion_service.ingest_market_snapshot(
        "US",
        date(2026, 1, 1),
        date(2026, 1, 2),
        provider_name="mock",
    )

    quality_diagnostics = snapshot["quality_diagnostics"]

    assert quality_diagnostics["status"] == "FAIL"
    assert quality_diagnostics["instrument_count"] == 0
    assert quality_diagnostics["instruments"] == []
    assert quality_diagnostics["quality_error"] == "No instruments available for quality diagnostics."


def test_ingest_mock_market_snapshot_remains_compatible():
    snapshot = ingest_mock_market_snapshot(
        "US",
        date(2026, 1, 1),
        date(2026, 1, 2),
        provider_name="mock",
    )

    assert snapshot["market"] == "US"
    assert snapshot["provider"] == "mock"
    assert snapshot["status"] == "ingested"
