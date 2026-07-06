import csv
import json
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.domain.models import MarketIndicatorObservation
from packages.services.market_indicators import (
    DEFAULT_MARKET_INDICATOR_DEFINITIONS,
    MarketIndicatorSeedImportError,
    MarketIndicatorObservationSeed,
    get_latest_market_indicator_payload,
    get_macro_indicator_payloads,
    import_market_indicator_observation_seed_file,
    parse_market_indicator_observation_seed_file,
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

    assert result == {"definitions": len(DEFAULT_MARKET_INDICATOR_DEFINITIONS), "observations": 0}
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


def test_get_macro_indicator_payloads_returns_curated_no_data_library():
    session = make_session()

    payloads = get_macro_indicator_payloads(session=session)
    codes = [payload["code"] for payload in payloads]

    assert codes == [
        "buffett_indicator_cn",
        "buffett_indicator_hk",
        "buffett_indicator_us",
        "us_10y_yield",
        "us_2y_yield",
        "us_10y_2y_spread",
        "us_cpi_yoy",
        "us_m2_yoy",
        "cn_m2_yoy",
    ]
    assert {payload["category"] for payload in payloads} >= {"valuation", "rates", "inflation", "liquidity"}
    assert all(payload["status"] == "no_data" for payload in payloads)


def test_get_macro_indicator_payloads_includes_audited_observation_metadata():
    session = make_session()
    seed_market_indicators(session=session)
    upsert_market_indicator_observation(
        MarketIndicatorObservationSeed(
            code="us_10y_yield",
            as_of=date(2026, 7, 3),
            value=Decimal("4.250000"),
            source="Audited seed: FRED DGS10",
            components={
                "source_series_id": "DGS10",
                "source_url": "https://fred.stlouisfed.org/series/DGS10",
                "methodology": "Daily 10-year Treasury constant maturity rate.",
                "notes": "Operator-reviewed seed value; not a live feed.",
            },
        ),
        session=session,
    )

    payloads = get_macro_indicator_payloads(session=session)
    payload_by_code = {payload["code"]: payload for payload in payloads}

    assert payload_by_code["us_10y_yield"]["status"] == "ok"
    assert payload_by_code["us_10y_yield"]["value"] == 4.25
    assert payload_by_code["us_10y_yield"]["source"] == "Audited seed: FRED DGS10"
    assert payload_by_code["us_10y_yield"]["components"]["source_series_id"] == "DGS10"


def test_import_market_indicator_observation_seed_file_accepts_json(tmp_path):
    session = make_session()
    seed_file = tmp_path / "macro-seeds.json"
    seed_file.write_text(
        json.dumps(
            {
                "observations": [
                    {
                        "code": "us_10y_yield",
                        "as_of": "2026-07-03",
                        "value": "4.250000",
                        "source": "Audited seed: FRED DGS10",
                        "components": {
                            "source_series_id": "DGS10",
                            "source_url": "https://fred.stlouisfed.org/series/DGS10",
                            "methodology": "Daily 10-year Treasury constant maturity rate.",
                            "notes": "Operator-reviewed seed value; not a live feed.",
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    result = import_market_indicator_observation_seed_file(seed_file, session=session)
    payload = get_latest_market_indicator_payload("us_10y_yield", session=session)

    assert result.observations == 1
    assert result.codes == ("us_10y_yield",)
    assert result.latest_as_of == "2026-07-03"
    assert payload["status"] == "ok"
    assert payload["value"] == 4.25
    assert payload["source"] == "Audited seed: FRED DGS10"


def test_import_market_indicator_observation_seed_file_accepts_csv(tmp_path):
    session = make_session()
    seed_file = tmp_path / "macro-seeds.csv"
    with seed_file.open("w", encoding="utf-8", newline="") as file_handle:
        writer = csv.DictWriter(
            file_handle,
            fieldnames=["code", "as_of", "value", "source", "components_json"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "code": "us_cpi_yoy",
                "as_of": "2026-06-30",
                "value": "3.100000",
                "source": "Audited seed: FRED CPIAUCSL derived YoY",
                "components_json": json.dumps(
                    {
                        "source_series_id": "CPIAUCSL",
                        "source_url": "https://fred.stlouisfed.org/series/CPIAUCSL",
                        "calculation": "Year-over-year percent change from reviewed CPI index.",
                    }
                ),
            }
        )

    result = import_market_indicator_observation_seed_file(seed_file, session=session)
    payload = get_latest_market_indicator_payload("us_cpi_yoy", session=session)

    assert result.observations == 1
    assert payload["status"] == "ok"
    assert payload["value"] == 3.1
    assert payload["components"]["calculation"] == "Year-over-year percent change from reviewed CPI index."


def test_parse_market_indicator_observation_seed_file_rejects_missing_audit_metadata(tmp_path):
    seed_file = tmp_path / "macro-seeds.json"
    seed_file.write_text(
        json.dumps(
            [
                {
                    "code": "us_10y_yield",
                    "as_of": "2026-07-03",
                    "value": "4.250000",
                    "source": "Audited seed: FRED DGS10",
                    "components": {"source_series_id": "DGS10"},
                }
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(MarketIndicatorSeedImportError) as error:
        parse_market_indicator_observation_seed_file(seed_file)

    assert "row 1" in str(error.value)
    assert "components must include one of" in str(error.value)
    assert "methodology" in str(error.value)


def test_import_market_indicator_observation_seed_file_rejects_unknown_code_atomically(tmp_path):
    session = make_session()
    seed_market_indicators(session=session)
    seed_file = tmp_path / "macro-seeds.json"
    seed_file.write_text(
        json.dumps(
            [
                {
                    "code": "us_10y_yield",
                    "as_of": "2026-07-03",
                    "value": "4.250000",
                    "source": "Audited seed: FRED DGS10",
                    "components": {
                        "source_series_id": "DGS10",
                        "methodology": "Daily 10-year Treasury constant maturity rate.",
                    },
                },
                {
                    "code": "unknown_macro_code",
                    "as_of": "2026-07-03",
                    "value": "1.000000",
                    "source": "Audited seed: example",
                    "components": {
                        "source_name": "Example source",
                        "notes": "Reviewed but unsupported indicator code.",
                    },
                },
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(MarketIndicatorSeedImportError) as error:
        import_market_indicator_observation_seed_file(seed_file, session=session)

    payload = get_latest_market_indicator_payload("us_10y_yield", session=session)
    assert "unknown_macro_code" in str(error.value)
    assert session.query(MarketIndicatorObservation).count() == 0
    assert payload["status"] == "no_data"
