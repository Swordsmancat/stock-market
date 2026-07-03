from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from packages.domain.models import MarketIndicator, MarketIndicatorObservation


BUFFETT_INDICATOR_CATEGORY = "valuation"
BUFFETT_INDICATOR_UNIT = "percent"
BUFFETT_INDICATOR_REGIONS = ("CN", "HK", "US")


@dataclass(frozen=True)
class MarketIndicatorDefinition:
    code: str
    name: str
    category: str
    region: str
    unit: str
    description: str
    display_order: int
    is_active: bool = True


@dataclass(frozen=True)
class MarketIndicatorObservationSeed:
    code: str
    as_of: date
    value: Decimal
    source: str
    components: dict[str, Any]


DEFAULT_MARKET_INDICATOR_DEFINITIONS: tuple[MarketIndicatorDefinition, ...] = (
    MarketIndicatorDefinition(
        code="buffett_indicator_cn",
        name="Buffett Indicator - China",
        category=BUFFETT_INDICATOR_CATEGORY,
        region="CN",
        unit=BUFFETT_INDICATOR_UNIT,
        description="Total listed-market capitalization divided by GDP for China.",
        display_order=10,
    ),
    MarketIndicatorDefinition(
        code="buffett_indicator_hk",
        name="Buffett Indicator - Hong Kong",
        category=BUFFETT_INDICATOR_CATEGORY,
        region="HK",
        unit=BUFFETT_INDICATOR_UNIT,
        description="Hong Kong listed-market capitalization divided by GDP.",
        display_order=20,
    ),
    MarketIndicatorDefinition(
        code="buffett_indicator_us",
        name="Buffett Indicator - United States",
        category=BUFFETT_INDICATOR_CATEGORY,
        region="US",
        unit=BUFFETT_INDICATOR_UNIT,
        description="Total listed-market capitalization divided by GDP for the United States.",
        display_order=30,
    ),
)

# Real observations should be added only when source and component values are auditable.
# Keeping this empty is intentional: the dashboard returns explicit no-data until a
# verified seed file or operator-provided seed is loaded.
DEFAULT_MARKET_INDICATOR_OBSERVATIONS: tuple[MarketIndicatorObservationSeed, ...] = ()


def _decimal_to_float(value: Decimal | None) -> float | None:
    return None if value is None else float(value)


def upsert_market_indicator_definition(
    definition: MarketIndicatorDefinition,
    session: Session,
    commit: bool = True,
) -> MarketIndicator:
    indicator = (
        session.query(MarketIndicator)
        .filter(MarketIndicator.code == definition.code)
        .first()
    )
    if indicator is None:
        indicator = MarketIndicator(code=definition.code)
        session.add(indicator)

    indicator.name = definition.name
    indicator.category = definition.category
    indicator.region = definition.region
    indicator.unit = definition.unit
    indicator.description = definition.description
    indicator.display_order = definition.display_order
    indicator.is_active = definition.is_active
    session.flush()

    if commit:
        session.commit()
    return indicator


def upsert_market_indicator_observation(
    seed: MarketIndicatorObservationSeed,
    session: Session,
    commit: bool = True,
) -> MarketIndicatorObservation:
    indicator = (
        session.query(MarketIndicator)
        .filter(MarketIndicator.code == seed.code)
        .first()
    )
    if indicator is None:
        msg = f"Market indicator definition does not exist: {seed.code}"
        raise ValueError(msg)

    observation = (
        session.query(MarketIndicatorObservation)
        .filter(MarketIndicatorObservation.indicator_id == indicator.id)
        .filter(MarketIndicatorObservation.as_of == seed.as_of)
        .first()
    )
    if observation is None:
        observation = MarketIndicatorObservation(
            indicator_id=indicator.id,
            as_of=seed.as_of,
        )
        session.add(observation)

    observation.value = seed.value
    observation.source = seed.source
    observation.components_json = seed.components
    session.flush()

    if commit:
        session.commit()
    return observation


def seed_market_indicators(
    session: Session,
    definitions: tuple[MarketIndicatorDefinition, ...] = DEFAULT_MARKET_INDICATOR_DEFINITIONS,
    observations: tuple[MarketIndicatorObservationSeed, ...] = DEFAULT_MARKET_INDICATOR_OBSERVATIONS,
) -> dict[str, int]:
    for definition in definitions:
        upsert_market_indicator_definition(definition, session=session, commit=False)
    for observation in observations:
        upsert_market_indicator_observation(observation, session=session, commit=False)
    session.commit()
    return {
        "definitions": len(definitions),
        "observations": len(observations),
    }


def get_latest_market_indicator_payload(code: str, session: Session) -> dict[str, object]:
    indicator = (
        session.query(MarketIndicator)
        .filter(MarketIndicator.code == code)
        .filter(MarketIndicator.is_active.is_(True))
        .first()
    )
    if indicator is None:
        return {
            "code": code,
            "name": code,
            "region": None,
            "category": None,
            "status": "no_data",
            "value": None,
            "unit": None,
            "as_of": None,
            "source": None,
            "components": {},
            "no_data_reason": "Indicator definition is not available.",
        }

    observation = (
        session.query(MarketIndicatorObservation)
        .filter(MarketIndicatorObservation.indicator_id == indicator.id)
        .order_by(MarketIndicatorObservation.as_of.desc())
        .first()
    )
    if observation is None:
        return {
            "code": indicator.code,
            "name": indicator.name,
            "region": indicator.region,
            "category": indicator.category,
            "status": "no_data",
            "value": None,
            "unit": indicator.unit,
            "as_of": None,
            "source": None,
            "components": {},
            "no_data_reason": "No audited observation has been seeded for this indicator yet.",
        }

    return {
        "code": indicator.code,
        "name": indicator.name,
        "region": indicator.region,
        "category": indicator.category,
        "status": "ok",
        "value": _decimal_to_float(observation.value),
        "unit": indicator.unit,
        "as_of": observation.as_of.isoformat(),
        "source": observation.source,
        "components": observation.components_json,
        "no_data_reason": None,
    }


def get_buffett_indicator_payloads(session: Session) -> list[dict[str, object]]:
    seed_market_indicators(session=session)
    codes = [f"buffett_indicator_{region.lower()}" for region in BUFFETT_INDICATOR_REGIONS]
    return [get_latest_market_indicator_payload(code, session=session) for code in codes]
