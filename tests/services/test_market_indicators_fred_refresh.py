from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.domain.models import MarketIndicatorObservation
from packages.providers.fred_provider import FredObservation
from packages.providers.fred_provider import FredSeriesObservations
from packages.services import market_indicators as market_indicators_service
from packages.services.market_indicators import FredMacroSeriesTarget
from packages.services.market_indicators import get_latest_market_indicator_payload
from packages.services.market_indicators import refresh_fred_macro_indicators
from packages.shared.database import Base


class FakeFredProvider:
    def __init__(self, payloads):
        self.payloads = payloads
        self.calls = []

    def fetch_series_observations(self, series_id, *, observation_start, observation_end):
        self.calls.append((series_id, observation_start, observation_end))
        return self.payloads[series_id]


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def fred_result(series_id, rows, skipped=()):
    return FredSeriesObservations(
        series_id=series_id,
        observations=tuple(
            FredObservation(
                series_id=series_id,
                as_of=row_date,
                value=Decimal(row_value),
                raw_value=str(row_value),
            )
            for row_date, row_value in rows
        ),
        skipped=tuple(skipped),
    )


def test_refresh_fred_macro_indicators_writes_direct_rate_observations():
    session = make_session()
    provider = FakeFredProvider(
        {
            "DGS10": fred_result("DGS10", [(date(2026, 7, 1), "4.25")]),
            "DGS2": fred_result("DGS2", [(date(2026, 7, 1), "3.95")]),
            "T10Y2Y": fred_result("T10Y2Y", [(date(2026, 7, 1), "0.30")]),
        }
    )

    result = refresh_fred_macro_indicators(
        session=session,
        series_group="rates",
        start=date(2026, 7, 1),
        end=date(2026, 7, 1),
        provider=provider,
        retrieved_at=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )

    payload = get_latest_market_indicator_payload("us_10y_yield", session=session)

    assert result.observations == 3
    assert result.codes == ("us_10y_2y_spread", "us_10y_yield", "us_2y_yield")
    assert payload["status"] == "ok"
    assert payload["value"] == 4.25
    assert payload["source"] == "FRED DGS10"
    assert payload["components"]["source_series_id"] == "DGS10"
    assert payload["components"]["retrieved_at"] == "2026-07-02T00:00:00+00:00"


def test_refresh_fred_macro_indicators_derives_cpi_yoy_with_audit_components():
    session = make_session()
    provider = FakeFredProvider(
        {
            "CPIAUCSL": fred_result(
                "CPIAUCSL",
                [
                    (date(2025, 6, 1), "100"),
                    (date(2026, 6, 1), "110"),
                ],
            )
        }
    )

    result = refresh_fred_macro_indicators(
        session=session,
        series_group="inflation",
        start=date(2026, 6, 1),
        end=date(2026, 6, 1),
        provider=provider,
        retrieved_at=datetime(2026, 7, 2, tzinfo=timezone.utc),
    )

    payload = get_latest_market_indicator_payload("us_cpi_yoy", session=session)

    assert result.observations == 1
    assert payload["status"] == "ok"
    assert payload["value"] == 10.0
    assert payload["source"] == "FRED CPIAUCSL derived YoY"
    assert payload["components"]["calculation"] == "((current_value / prior_year_value) - 1) * 100"
    assert payload["components"]["source_observation_dates"] == {
        "current": "2026-06-01",
        "prior_year": "2025-06-01",
    }


def test_refresh_fred_macro_indicators_dry_run_does_not_write_observations():
    session = make_session()
    provider = FakeFredProvider(
        {"DGS10": fred_result("DGS10", [(date(2026, 7, 1), "4.25")])}
    )

    result = refresh_fred_macro_indicators(
        session=session,
        series_group="DGS10",
        start=date(2026, 7, 1),
        end=date(2026, 7, 1),
        dry_run=True,
        provider=provider,
    )

    assert result.dry_run is True
    assert result.observations == 1
    assert session.query(MarketIndicatorObservation).count() == 0


def test_refresh_fred_macro_indicators_rolls_back_invalid_target(monkeypatch):
    session = make_session()
    provider = FakeFredProvider(
        {"BAD": fred_result("BAD", [(date(2026, 7, 1), "1.0")])}
    )
    monkeypatch.setattr(
        market_indicators_service,
        "FRED_MACRO_SERIES",
        (
            FredMacroSeriesTarget(
                series_id="BAD",
                target_code="unknown_indicator",
                group="bad",
                handling=market_indicators_service.FRED_DIRECT_HANDLING,
                methodology="Bad test target.",
            ),
        ),
    )

    with pytest.raises(
        market_indicators_service.MarketIndicatorSeedImportError,
        match="unknown_indicator",
    ):
        refresh_fred_macro_indicators(
            session=session,
            series_group="bad",
            start=date(2026, 7, 1),
            end=date(2026, 7, 1),
            provider=provider,
        )

    assert session.query(MarketIndicatorObservation).count() == 0
