from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.domain.models import MarketIndicatorObservation
from packages.providers.world_bank_provider import WorldBankIndicatorObservations
from packages.providers.world_bank_provider import WorldBankObservation
from packages.providers.world_bank_provider import WorldBankSkippedObservation
from packages.services import market_indicators as market_indicators_service
from packages.services.market_indicators import WorldBankMacroTarget
from packages.services.market_indicators import get_latest_market_indicator_payload
from packages.services.market_indicators import refresh_world_bank_macro_indicators
from packages.shared.database import Base


class FakeWorldBankProvider:
    def __init__(self, payloads):
        self.payloads = payloads
        self.calls = []

    def fetch_country_indicator_observations(
        self,
        country_code,
        indicator_id,
        *,
        start_year=None,
        end_year=None,
        most_recent_values=None,
    ):
        self.calls.append(
            (country_code, indicator_id, start_year, end_year, most_recent_values)
        )
        return self.payloads[(country_code, indicator_id)]


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def world_bank_result(country_code, indicator_id, rows, skipped=()):
    return WorldBankIndicatorObservations(
        country_code=country_code,
        indicator_id=indicator_id,
        observations=tuple(
            WorldBankObservation(
                country_code=country_code,
                indicator_id=indicator_id,
                as_of=row_date,
                value=Decimal(row_value),
                raw_value=str(row_value),
                country_name=row_country_name,
                indicator_name=row_indicator_name,
            )
            for row_date, row_value, row_country_name, row_indicator_name in rows
        ),
        skipped=tuple(skipped),
    )


def test_refresh_world_bank_macro_indicators_writes_latest_buffett_observation():
    session = make_session()
    provider = FakeWorldBankProvider(
        {
            ("USA", "CM.MKT.LCAP.GD.ZS"): world_bank_result(
                "USA",
                "CM.MKT.LCAP.GD.ZS",
                [
                    (
                        date(2024, 12, 31),
                        "194.250000",
                        "United States",
                        "Market capitalization of listed domestic companies (% of GDP)",
                    )
                ],
            ),
            ("USA", "NY.GDP.MKTP.CD"): world_bank_result(
                "USA",
                "NY.GDP.MKTP.CD",
                [
                    (
                        date(2024, 12, 31),
                        "29184800000000",
                        "United States",
                        "GDP (current US$)",
                    )
                ],
            ),
        }
    )

    result = refresh_world_bank_macro_indicators(
        session=session,
        target_group="US",
        provider=provider,
        retrieved_at=datetime(2026, 7, 7, tzinfo=timezone.utc),
    )

    payload = get_latest_market_indicator_payload("buffett_indicator_us", session=session)

    assert result.observations == 1
    assert result.fetched == 2
    assert result.skipped == 0
    assert result.codes == ("buffett_indicator_us",)
    assert result.latest_as_of == "2024-12-31"
    assert provider.calls == [
        ("USA", "CM.MKT.LCAP.GD.ZS", None, None, 1),
        ("USA", "NY.GDP.MKTP.CD", None, None, 1),
    ]
    assert payload["status"] == "ok"
    assert payload["value"] == 194.25
    assert payload["source"] == "World Bank CM.MKT.LCAP.GD.ZS USA"
    assert payload["components"]["provider"] == "world_bank"
    assert payload["components"]["country_code"] == "USA"
    assert payload["components"]["source_indicator_id"] == "CM.MKT.LCAP.GD.ZS"
    assert payload["components"]["gdp_current_usd"] == "29184800000000"
    assert payload["components"]["gdp_source_indicator_id"] == "NY.GDP.MKTP.CD"
    assert payload["components"]["retrieved_at"] == "2026-07-07T00:00:00+00:00"
    assert payload["components"]["source_observation_dates"] == {
        "ratio": "2024-12-31",
        "gdp": "2024-12-31",
    }


def test_refresh_world_bank_macro_indicators_dry_run_does_not_write_observations():
    session = make_session()
    provider = FakeWorldBankProvider(
        {
            ("USA", "CM.MKT.LCAP.GD.ZS"): world_bank_result(
                "USA",
                "CM.MKT.LCAP.GD.ZS",
                [
                    (
                        date(2024, 12, 31),
                        "194.250000",
                        "United States",
                        "Market capitalization of listed domestic companies (% of GDP)",
                    )
                ],
            ),
            ("USA", "NY.GDP.MKTP.CD"): world_bank_result(
                "USA",
                "NY.GDP.MKTP.CD",
                [
                    (
                        date(2024, 12, 31),
                        "29184800000000",
                        "United States",
                        "GDP (current US$)",
                    )
                ],
            ),
        }
    )

    result = refresh_world_bank_macro_indicators(
        session=session,
        target_group="buffett_indicator_us",
        dry_run=True,
        provider=provider,
    )

    assert result.dry_run is True
    assert result.observations == 1
    assert session.query(MarketIndicatorObservation).count() == 0


def test_refresh_world_bank_macro_indicators_reports_skipped_primary_rows():
    session = make_session()
    provider = FakeWorldBankProvider(
        {
            ("USA", "CM.MKT.LCAP.GD.ZS"): world_bank_result(
                "USA",
                "CM.MKT.LCAP.GD.ZS",
                [],
                skipped=(
                    WorldBankSkippedObservation(
                        country_code="USA",
                        indicator_id="CM.MKT.LCAP.GD.ZS",
                        reason="missing_or_invalid_value",
                        raw_date="2024",
                        raw_value=None,
                    ),
                ),
            ),
            ("USA", "NY.GDP.MKTP.CD"): world_bank_result(
                "USA",
                "NY.GDP.MKTP.CD",
                [],
            ),
        }
    )

    result = refresh_world_bank_macro_indicators(
        session=session,
        target_group="USA",
        provider=provider,
    )

    assert result.observations == 0
    assert result.skipped == 1
    assert result.diagnostics == (
        "World Bank USA CM.MKT.LCAP.GD.ZS skipped 1 missing or invalid observations.",
    )
    assert session.query(MarketIndicatorObservation).count() == 0


def test_refresh_world_bank_macro_indicators_rolls_back_invalid_target(monkeypatch):
    session = make_session()
    provider = FakeWorldBankProvider(
        {
            ("USA", "CM.MKT.LCAP.GD.ZS"): world_bank_result(
                "USA",
                "CM.MKT.LCAP.GD.ZS",
                [
                    (
                        date(2024, 12, 31),
                        "194.250000",
                        "United States",
                        "Market capitalization of listed domestic companies (% of GDP)",
                    )
                ],
            ),
            ("USA", "NY.GDP.MKTP.CD"): world_bank_result(
                "USA",
                "NY.GDP.MKTP.CD",
                [
                    (
                        date(2024, 12, 31),
                        "29184800000000",
                        "United States",
                        "GDP (current US$)",
                    )
                ],
            ),
        }
    )
    monkeypatch.setattr(
        market_indicators_service,
        "WORLD_BANK_BUFFETT_TARGETS",
        (
            WorldBankMacroTarget(
                country_code="USA",
                target_code="unknown_indicator",
                group="buffett",
                indicator_id="CM.MKT.LCAP.GD.ZS",
                methodology="Bad test target.",
            ),
        ),
    )

    with pytest.raises(
        market_indicators_service.MarketIndicatorSeedImportError,
        match="unknown_indicator",
    ):
        refresh_world_bank_macro_indicators(
            session=session,
            target_group="buffett",
            provider=provider,
        )

    assert session.query(MarketIndicatorObservation).count() == 0


def test_refresh_world_bank_macro_indicators_rejects_unknown_target():
    session = make_session()

    with pytest.raises(ValueError, match="Unsupported World Bank macro target"):
        refresh_world_bank_macro_indicators(
            session=session,
            target_group="not-a-target",
            provider=FakeWorldBankProvider({}),
        )
