from datetime import date

import pytest

from packages.services import market_data as market_data_service
from packages.services.market_data import (
    MarketDataProviderError,
    MarketDataProviderPayloadError,
    MarketDataProviderRateLimitError,
    MarketDataProviderTimeoutError,
    MarketDataProviderUnavailableError,
    get_bars_payload,
    get_indicator_payload,
    get_latest_bar_payload,
    get_latest_bars_batch_payload,
    get_market_snapshot,
)


def test_get_bars_payload_serializes_provider_bars():
    payload = get_bars_payload(
        "AAPL",
        "1d",
        date(2026, 1, 1),
        date(2026, 1, 3),
        provider_name="mock",
    )

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


def test_get_bars_payload_uses_platform_default_when_provider_is_omitted(monkeypatch):
    monkeypatch.setattr(
        market_data_service,
        "get_effective_market_data_provider",
        lambda requested=None: "mock" if requested is None else str(requested).strip().lower(),
    )

    payload = get_bars_payload(
        "AAPL",
        "1d",
        date(2026, 1, 1),
        date(2026, 1, 1),
        provider_name=None,
    )

    assert payload["source"] == "mock"


def test_get_indicator_payload_returns_latest_values():
    payload = get_indicator_payload(
        "AAPL",
        date(2026, 1, 1),
        date(2026, 1, 15),
        3,
        provider_name="mock",
    )

    assert payload["symbol"] == "AAPL"
    assert payload["indicators"]["ma"] == 114.0
    assert 0 <= payload["indicators"]["rsi"] <= 100


def test_get_indicator_payload_handles_empty_bars():
    payload = get_indicator_payload(
        "AAPL",
        date(2026, 1, 2),
        date(2026, 1, 1),
        3,
        provider_name="mock",
    )

    assert payload["symbol"] == "AAPL"
    assert payload["as_of"] is None
    assert payload["indicators"] == {"ma": None, "rsi": None}


def test_get_indicator_payload_returns_nulls_for_insufficient_ma_data():
    payload = get_indicator_payload(
        "AAPL",
        date(2026, 1, 1),
        date(2026, 1, 2),
        3,
        provider_name="mock",
    )

    assert payload["symbol"] == "AAPL"
    assert payload["as_of"] == "2026-01-02"
    assert payload["indicators"]["ma"] is None
    assert payload["indicators"]["rsi"] is None


def test_get_bars_payload_wraps_unexpected_provider_failures(monkeypatch):
    class FailingProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(self, symbol: str, timeframe: str, start: date, end: date) -> list:
            raise RuntimeError("provider unavailable token=secret123")

    def get_failing_provider(provider_name: str = "mock") -> FailingProvider:
        return FailingProvider()

    monkeypatch.setattr(market_data_service, "get_provider", get_failing_provider)

    with pytest.raises(MarketDataProviderError) as raised_error:
        get_bars_payload(
            "AAPL",
            "1d",
            date(2026, 1, 1),
            date(2026, 1, 1),
            provider_name="mock",
        )

    provider_error = raised_error.value
    assert provider_error.provider_name == "mock"
    assert provider_error.operation == "fetching bars"
    assert isinstance(provider_error.original_error, RuntimeError)
    assert provider_error.category == "provider_error"
    assert provider_error.http_status_code == 502
    assert "secret123" not in str(provider_error)
    assert "secret123" in str(provider_error.original_error)


def test_get_bars_payload_preserves_provider_value_errors(monkeypatch):
    class FailingProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(self, symbol: str, timeframe: str, start: date, end: date) -> list:
            raise ValueError("unsupported timeframe")

    def get_failing_provider(provider_name: str = "mock") -> FailingProvider:
        return FailingProvider()

    monkeypatch.setattr(market_data_service, "get_provider", get_failing_provider)

    with pytest.raises(ValueError, match="unsupported timeframe"):
        get_bars_payload(
            "AAPL",
            "1h",
            date(2026, 1, 1),
            date(2026, 1, 1),
            provider_name="mock",
        )


@pytest.mark.parametrize(
    ("provider_exception", "expected_error_type", "expected_category", "expected_status_code"),
    [
        (TimeoutError("request timed out"), MarketDataProviderTimeoutError, "timeout", 504),
        (ConnectionError("connection refused"), MarketDataProviderUnavailableError, "unavailable", 503),
        (
            RuntimeError("upstream rate limit exceeded"),
            MarketDataProviderRateLimitError,
            "rate_limited",
            429,
        ),
    ],
)
def test_get_bars_payload_classifies_provider_failures(
    monkeypatch,
    provider_exception,
    expected_error_type,
    expected_category,
    expected_status_code,
):
    class FailingProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(self, symbol: str, timeframe: str, start: date, end: date) -> list:
            raise provider_exception

    def get_failing_provider(provider_name: str = "mock") -> FailingProvider:
        return FailingProvider()

    monkeypatch.setattr(market_data_service, "get_provider", get_failing_provider)

    with pytest.raises(expected_error_type) as raised_error:
        get_bars_payload(
            "AAPL",
            "1d",
            date(2026, 1, 1),
            date(2026, 1, 1),
            provider_name="mock",
        )

    provider_error = raised_error.value
    assert provider_error.provider_name == "mock"
    assert provider_error.operation == "fetching bars"
    assert provider_error.category == expected_category
    assert provider_error.http_status_code == expected_status_code


def test_get_bars_payload_wraps_malformed_provider_bar_payloads(monkeypatch):
    class MalformedProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(self, symbol: str, timeframe: str, start: date, end: date) -> list:
            return [object()]

    def get_malformed_provider(provider_name: str = "mock") -> MalformedProvider:
        return MalformedProvider()

    monkeypatch.setattr(market_data_service, "get_provider", get_malformed_provider)

    with pytest.raises(MarketDataProviderPayloadError) as raised_error:
        get_bars_payload(
            "AAPL",
            "1d",
            date(2026, 1, 1),
            date(2026, 1, 1),
            provider_name="mock",
        )

    provider_error = raised_error.value
    assert provider_error.provider_name == "mock"
    assert provider_error.operation == "serializing bars"
    assert provider_error.category == "malformed_payload"
    assert provider_error.http_status_code == 502


def test_get_market_snapshot_includes_instruments_and_bars():
    snapshot = get_market_snapshot(
        "US",
        date(2026, 1, 1),
        date(2026, 1, 2),
        provider_name="mock",
    )

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
