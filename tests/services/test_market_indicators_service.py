from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.services.market_indicators import (
    DEFAULT_MARKET_INDICATOR_DEFINITIONS,
    MarketIndicatorObservationSeed,
    get_latest_market_indicator_payload,
    seed_market_indicators,
    upsert_market_indicator_observation,
)
from packages.shared.database import Base


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_seed_market_indicators_creates_definitions_with_no_data_state():
    session = make_session()

    result = seed_market_indicators(session=session)
    payload = get_latest_market_indicator_payload("buffett_indicator_us", session=session)

    assert result == {"definitions": 3, "observations": 0}
    assert payload["code"] == "buffett_indicator_us"
    assert payload["name"] == "Buffett Indicator - United States"
    assert payload["status"] == "no_data"
    assert payload["value"] is None
    assert payload["components"] == {}


def test_upsert_market_indicator_observation_returns_auditable_latest_payload():
    session = make_session()
    seed_market_indicators(session=session)

    upsert_market_indicator_observation(
        MarketIndicatorObservationSeed(
            code="buffett_indicator_us",
            as_of=date(2026, 6, 30),
            value=Decimal("188.250000"),
            source="Audited seed: public market cap / GDP source note",
            components={
                "market_cap": 62000000000000,
                "gdp": 32934926958831,
                "ratio": 1.8825,
                "market_cap_source": "public market capitalization source",
                "gdp_source": "public GDP source",
            },
        ),
        session=session,
    )

    payload = get_latest_market_indicator_payload("buffett_indicator_us", session=session)

    assert payload["status"] == "ok"
    assert payload["value"] == 188.25
    assert payload["unit"] == "percent"
    assert payload["as_of"] == "2026-06-30"
    assert payload["source"] == "Audited seed: public market cap / GDP source note"
    assert payload["components"]["ratio"] == 1.8825


def test_get_latest_market_indicator_payload_handles_unknown_definition():
    session = make_session()

    payload = get_latest_market_indicator_payload("missing_indicator", session=session)

    assert payload["status"] == "no_data"
    assert payload["no_data_reason"] == "Indicator definition is not available."
