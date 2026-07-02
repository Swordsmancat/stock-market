from datetime import date

import pytest

from packages.services import market_data as market_data_service
from packages.services.market_data import (
    MarketDataProviderError,
    get_bars_payload,
    get_indicator_payload,
    get_latest_bar_payload,
    get_latest_bars_batch_payload,
    get_market_snapshot,
)


def test_get_bars_payload_serializes_provider_bars():
    payload = get_bars_payload("AAPL", "1d", date(2026, 1, 1), date(2026, 1, 3))

    assert payload["symbol"] == "AAPL"
    assert payload["timeframe"] == "1d"
    assert len(payload["items"]) == 3
    assert payload["items"][0]["close"] == 101.0


def test_get_bars_payload_reports_effective_provider_source():
    payload = get_bars_payload(
        "AAPL",
        "1d",
        date(2026, 1, 1),
        date(2026, 1, 1),
        provider_name=" Mock ",
    )

    assert payload["source"] == "mock"


def test_get_indicator_payload_returns_latest_values():
    payload = get_indicator_payload("AAPL", date(2026, 1, 1), date(2026, 1, 15), 3)

    assert payload["symbol"] == "AAPL"
    assert payload["indicators"]["ma"] == 114.0
    assert 0 <= payload["indicators"]["rsi"] <= 100


def test_get_indicator_payload_handles_empty_bars():
    payload = get_indicator_payload("AAPL", date(2026, 1, 2), date(2026, 1, 1), 3)

    assert payload["symbol"] == "AAPL"
    assert payload["as_of"] is None
    assert payload["indicators"] == {"ma": None, "rsi": None}


def test_get_indicator_payload_returns_nulls_for_insufficient_ma_data():
    payload = get_indicator_payload("AAPL", date(2026, 1, 1), date(2026, 1, 2), 3)

    assert payload["symbol"] == "AAPL"
    assert payload["as_of"] == "2026-01-02"
    assert payload["indicators"]["ma"] is None
    assert payload["indicators"]["rsi"] is None


def test_get_bars_payload_wraps_unexpected_provider_failures(monkeypatch):
    class FailingProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(self, symbol: str, timeframe: str, start: date, end: date) -> list:
            raise RuntimeError("provider unavailable")

    def get_failing_provider(provider_name: str = "mock") -> FailingProvider:
        return FailingProvider()

    monkeypatch.setattr(market_data_service, "get_provider", get_failing_provider)

    with pytest.raises(MarketDataProviderError) as raised_error:
        get_bars_payload("AAPL", "1d", date(2026, 1, 1), date(2026, 1, 1))

    provider_error = raised_error.value
    assert provider_error.provider_name == "mock"
    assert provider_error.operation == "fetching bars"
    assert isinstance(provider_error.original_error, RuntimeError)
    assert "provider unavailable" in str(provider_error)


def test_get_market_snapshot_includes_instruments_and_bars():
    snapshot = get_market_snapshot("US", date(2026, 1, 1), date(2026, 1, 2))

    assert snapshot["market"] == "US"
    assert snapshot["instrument_count"] == 1
    assert snapshot["instruments"][0]["symbol"] == "AAPL"
    assert len(snapshot["instruments"][0]["bars"]) == 2


def test_get_latest_bar_payload_uses_provider_when_database_empty():
    payload = get_latest_bar_payload("AAPL", session=None, provider_name="mock")

    assert payload["symbol"] == "AAPL"
    assert payload["item"] is not None
    assert float(payload["item"]["close"]) > 0


def test_get_latest_bars_batch_payload_returns_one_entry_per_symbol():
    payload = get_latest_bars_batch_payload(["AAPL", "0700"], session=None, provider_name="mock")

    assert len(payload["items"]) == 2
    assert payload["items"][0]["symbol"] == "AAPL"
    assert payload["items"][0]["item"] is not None
