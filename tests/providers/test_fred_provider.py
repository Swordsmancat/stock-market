from datetime import date
from decimal import Decimal

import pytest

from packages.providers.fred_provider import FredProvider
from packages.providers.fred_provider import FredProviderConfigurationError
from packages.providers.fred_provider import FredProviderError


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_fred_provider_parses_series_observations():
    def fake_getter(url, *, params, timeout):
        assert url == "https://api.stlouisfed.org/fred/series/observations"
        assert params["api_key"] == "test-key"
        assert params["series_id"] == "DGS10"
        assert timeout == 10.0
        return FakeResponse(
            {
                "observations": [
                    {
                        "date": "2026-07-01",
                        "value": "4.2500",
                        "realtime_start": "2026-07-02",
                        "realtime_end": "2026-07-02",
                    }
                ]
            }
        )

    provider = FredProvider(api_key="test-key", http_getter=fake_getter)

    result = provider.fetch_series_observations(
        "dgs10",
        observation_start=date(2026, 7, 1),
        observation_end=date(2026, 7, 2),
    )

    assert result.series_id == "DGS10"
    assert result.skipped == ()
    assert result.observations[0].as_of == date(2026, 7, 1)
    assert result.observations[0].value == Decimal("4.2500")
    assert result.observations[0].realtime_start == "2026-07-02"


def test_fred_provider_skips_missing_and_invalid_values():
    provider = FredProvider(
        api_key="test-key",
        http_getter=lambda *_args, **_kwargs: {
            "observations": [
                {"date": "2026-07-01", "value": "."},
                {"date": "2026-07-02", "value": ""},
                {"date": "bad-date", "value": "4.1"},
                {"date": "2026-07-03", "value": "4.2"},
            ]
        },
    )

    result = provider.fetch_series_observations(
        "DGS10",
        observation_start=date(2026, 7, 1),
        observation_end=date(2026, 7, 3),
    )

    assert [observation.value for observation in result.observations] == [Decimal("4.2")]
    assert [skipped.reason for skipped in result.skipped] == [
        "missing_or_invalid_value",
        "missing_or_invalid_value",
        "invalid_date",
    ]


def test_fred_provider_requires_api_key_without_requesting_network():
    called = False

    def fake_getter(*_args, **_kwargs):
        nonlocal called
        called = True
        return {}

    provider = FredProvider(api_key=None, http_getter=fake_getter)

    with pytest.raises(FredProviderConfigurationError, match="FRED API key is not configured"):
        provider.fetch_series_observations(
            "DGS10",
            observation_start=date(2026, 7, 1),
            observation_end=date(2026, 7, 2),
        )

    assert called is False


def test_fred_provider_sanitizes_http_errors():
    def fake_getter(*_args, **_kwargs):
        raise RuntimeError("provider failed with api_key=secret-key")

    provider = FredProvider(api_key="secret-key", http_getter=fake_getter)

    with pytest.raises(FredProviderError) as raised_error:
        provider.fetch_series_observations(
            "DGS10",
            observation_start=date(2026, 7, 1),
            observation_end=date(2026, 7, 2),
        )

    assert "secret-key" not in str(raised_error.value)
    assert "RuntimeError" in str(raised_error.value)
