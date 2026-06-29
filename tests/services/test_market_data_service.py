from datetime import date

from packages.services.market_data import (
    get_bars_payload,
    get_indicator_payload,
    get_market_snapshot,
)


def test_get_bars_payload_serializes_provider_bars():
    payload = get_bars_payload("AAPL", "1d", date(2026, 1, 1), date(2026, 1, 3))

    assert payload["symbol"] == "AAPL"
    assert payload["timeframe"] == "1d"
    assert len(payload["items"]) == 3
    assert payload["items"][0]["close"] == 101.0


def test_get_indicator_payload_returns_latest_values():
    payload = get_indicator_payload("AAPL", date(2026, 1, 1), date(2026, 1, 15), 3)

    assert payload["symbol"] == "AAPL"
    assert payload["indicators"]["ma"] == 114.0
    assert 0 <= payload["indicators"]["rsi"] <= 100


def test_get_market_snapshot_includes_instruments_and_bars():
    snapshot = get_market_snapshot("US", date(2026, 1, 1), date(2026, 1, 2))

    assert snapshot["market"] == "US"
    assert snapshot["instrument_count"] == 1
    assert snapshot["instruments"][0]["symbol"] == "AAPL"
    assert len(snapshot["instruments"][0]["bars"]) == 2
