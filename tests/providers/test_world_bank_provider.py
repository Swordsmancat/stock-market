from datetime import date
from decimal import Decimal

import pytest

from packages.providers.world_bank_provider import WorldBankProvider
from packages.providers.world_bank_provider import WorldBankProviderError


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_world_bank_provider_parses_country_indicator_observations():
    def fake_getter(url, *, params, timeout):
        assert url == (
            "https://api.worldbank.org/v2/country/USA/indicator/CM.MKT.LCAP.GD.ZS"
        )
        assert params["format"] == "json"
        assert params["date"] == "2020:2024"
        assert params["mrnev"] == 3
        assert params["page"] == 1
        assert timeout == 10.0
        return FakeResponse(
            [
                {"page": 1, "pages": 1},
                [
                    {
                        "date": "2024",
                        "value": 194.25,
                        "country": {"id": "US", "value": "United States"},
                        "indicator": {
                            "id": "CM.MKT.LCAP.GD.ZS",
                            "value": "Market capitalization of listed domestic companies (% of GDP)",
                        },
                    }
                ],
            ]
        )

    provider = WorldBankProvider(http_getter=fake_getter)

    result = provider.fetch_country_indicator_observations(
        "usa",
        "cm.mkt.lcap.gd.zs",
        start_year=2020,
        end_year=2024,
        most_recent_values=3,
    )

    assert result.country_code == "USA"
    assert result.indicator_id == "CM.MKT.LCAP.GD.ZS"
    assert result.skipped == ()
    assert result.observations[0].as_of == date(2024, 12, 31)
    assert result.observations[0].value == Decimal("194.25")
    assert result.observations[0].country_name == "United States"
    assert "Market capitalization" in str(result.observations[0].indicator_name)


def test_world_bank_provider_skips_missing_and_invalid_rows():
    provider = WorldBankProvider(
        http_getter=lambda *_args, **_kwargs: [
            {"page": 1, "pages": 1},
            [
                {"date": "2024", "value": None},
                {"date": "bad-year", "value": "1.0"},
                {"date": "2023", "value": "not-a-number"},
                {"date": "2022", "value": "150.50"},
            ],
        ]
    )

    result = provider.fetch_country_indicator_observations(
        "USA",
        "CM.MKT.LCAP.GD.ZS",
    )

    assert [observation.value for observation in result.observations] == [Decimal("150.50")]
    assert [skipped.reason for skipped in result.skipped] == [
        "missing_or_invalid_value",
        "invalid_date",
        "missing_or_invalid_value",
    ]


def test_world_bank_provider_fetches_additional_pages():
    calls: list[int] = []

    def fake_getter(_url, *, params, _timeout=None, timeout=10.0):
        page = int(params["page"])
        calls.append(page)
        if page == 1:
            return [{"page": 1, "pages": 2}, [{"date": "2023", "value": "101"}]]
        return [{"page": 2, "pages": 2}, [{"date": "2024", "value": "102"}]]

    provider = WorldBankProvider(http_getter=fake_getter)

    result = provider.fetch_country_indicator_observations("USA", "NY.GDP.MKTP.CD")

    assert calls == [1, 2]
    assert [observation.as_of for observation in result.observations] == [
        date(2023, 12, 31),
        date(2024, 12, 31),
    ]


def test_world_bank_provider_rejects_unexpected_payload_shape():
    provider = WorldBankProvider(http_getter=lambda *_args, **_kwargs: {"bad": "shape"})

    with pytest.raises(WorldBankProviderError, match="metadata/data list"):
        provider.fetch_country_indicator_observations("USA", "CM.MKT.LCAP.GD.ZS")


def test_world_bank_provider_sanitizes_http_errors():
    def fake_getter(*_args, **_kwargs):
        raise RuntimeError("provider failed with token=secret")

    provider = WorldBankProvider(http_getter=fake_getter)

    with pytest.raises(WorldBankProviderError) as raised_error:
        provider.fetch_country_indicator_observations("USA", "CM.MKT.LCAP.GD.ZS")

    assert "secret" not in str(raised_error.value)
    assert "RuntimeError" in str(raised_error.value)
