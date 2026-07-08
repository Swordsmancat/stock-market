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
    MarketIndicatorSeedOverwriteRequiredError,
    get_latest_market_indicator_payload,
    get_macro_indicator_payloads,
    get_official_macro_source_status_payload,
    import_market_indicator_observation_seed_content,
    import_market_indicator_observation_seed_file,
    parse_market_indicator_observation_seed_content,
    parse_market_indicator_observation_seed_file,
    preview_market_indicator_observation_seed_content,
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


def test_official_macro_source_status_reports_configuration_without_secret(monkeypatch):
    session = make_session()
    monkeypatch.setattr("packages.services.market_indicators.settings.fred_api_key", "SECRET_FRED_TOKEN")

    payload = get_official_macro_source_status_payload(session=session)
    providers = {provider["provider"]: provider for provider in payload["providers"]}

    assert payload["status"] == "degraded"
    assert "SECRET_FRED_TOKEN" not in json.dumps(payload)
    assert providers["fred"]["status"] == "degraded"
    assert providers["fred"]["configured"] is True
    assert providers["fred"]["credential_required"] is True
    assert providers["fred"]["credential_configured"] is True
    assert providers["fred"]["credential_label"] == "FRED_API_KEY"
    assert providers["fred"]["indicator_codes"] == [
        "us_10y_yield",
        "us_2y_yield",
        "us_10y_2y_spread",
        "us_cpi_yoy",
        "us_m2_yoy",
    ]
    assert providers["fred"]["evidence_count"] == 0
    assert providers["fred"]["latest_as_of"] is None
    assert providers["fred"]["missing_indicator_codes"] == providers["fred"]["indicator_codes"]
    assert providers["world_bank"]["status"] == "degraded"
    assert providers["world_bank"]["configured"] is True
    assert providers["world_bank"]["credential_required"] is False
    assert providers["world_bank"]["credential_configured"] is True
    assert providers["world_bank"]["source_frequency"] == "annual_lagged"
    assert "annual and lagged" in providers["world_bank"]["freshness_policy"]


def test_official_macro_source_status_uses_local_observations_and_fred_blocker(monkeypatch):
    session = make_session()
    monkeypatch.setattr("packages.services.market_indicators.settings.fred_api_key", "")
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
            },
        ),
        session=session,
    )
    upsert_market_indicator_observation(
        MarketIndicatorObservationSeed(
            code="buffett_indicator_us",
            as_of=date(2024, 12, 31),
            value=Decimal("194.250000"),
            source="World Bank CM.MKT.LCAP.GD.ZS USA",
            components={
                "provider": "world_bank",
                "source_name": "World Bank",
                "country_code": "USA",
                "source_indicator_id": "CM.MKT.LCAP.GD.ZS",
                "source_url": "https://data.worldbank.org/indicator/CM.MKT.LCAP.GD.ZS",
                "methodology": "World Bank market capitalization as percent of GDP.",
            },
        ),
        session=session,
    )

    payload = get_official_macro_source_status_payload(session=session)
    providers = {provider["provider"]: provider for provider in payload["providers"]}

    assert payload["status"] == "needs_configuration"
    assert providers["fred"]["status"] == "needs_configuration"
    assert providers["fred"]["configured"] is False
    assert providers["fred"]["can_refresh_from_browser"] is False
    assert providers["fred"]["evidence_count"] == 1
    assert providers["fred"]["latest_as_of"] == "2026-07-03"
    assert "us_10y_yield" not in providers["fred"]["missing_indicator_codes"]
    assert "FRED_API_KEY" in providers["fred"]["recommended_next_action"]
    assert providers["world_bank"]["status"] == "degraded"
    assert providers["world_bank"]["evidence_count"] == 1
    assert providers["world_bank"]["latest_as_of"] == "2024-12-31"
    assert "buffett_indicator_us" not in providers["world_bank"]["missing_indicator_codes"]


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


def test_parse_market_indicator_observation_seed_content_accepts_json_with_filename_hint():
    content = json.dumps(
        {
            "observations": [
                {
                    "code": "us_10y_yield",
                    "as_of": "2026-07-03",
                    "value": "4.250000",
                    "source": "Audited seed: FRED DGS10",
                    "components": {
                        "source_series_id": "DGS10",
                        "methodology": "Daily 10-year Treasury constant maturity rate.",
                    },
                }
            ]
        }
    )

    seeds = parse_market_indicator_observation_seed_content(
        content,
        filename="macro-seeds.json",
    )

    assert len(seeds) == 1
    assert seeds[0].code == "us_10y_yield"
    assert seeds[0].value == Decimal("4.250000")


def test_preview_market_indicator_seed_content_reports_insert_without_writing():
    session = make_session()
    content = json.dumps(
        [
            {
                "code": "cn_m2_yoy",
                "as_of": "2026-06-30",
                "value": "8.300000",
                "source": "Audited seed: PBOC public monetary statistics",
                "components": {
                    "source_url": "https://example.com/pboc-m2-release",
                    "methodology": "Manual YoY value reviewed from public release.",
                },
            }
        ]
    )

    preview = preview_market_indicator_observation_seed_content(
        content,
        session=session,
        format_hint="json",
    )

    assert preview["status"] == "valid"
    assert preview["can_import"] is True
    assert preview["summary"]["inserts"] == 1
    assert preview["summary"]["updates"] == 0
    assert preview["rows"][0]["intent"] == "insert"
    assert preview["rows"][0]["name"] == "China M2 Money Supply YoY"
    assert preview["rows"][0]["metadata"] == {
        "source_present": True,
        "method_present": True,
    }
    assert session.query(MarketIndicatorObservation).count() == 0


def test_preview_market_indicator_seed_content_accepts_csv_text():
    session = make_session()
    content = "\n".join(
        [
            "code,as_of,value,source,components_json",
            'us_cpi_yoy,2026-06-30,3.100000,Audited seed: FRED CPIAUCSL derived YoY,"{""source_series_id"": ""CPIAUCSL"", ""calculation"": ""Reviewed YoY calculation.""}"',
        ]
    )

    preview = preview_market_indicator_observation_seed_content(
        content,
        session=session,
        filename="macro-seeds.csv",
    )

    assert preview["status"] == "valid"
    assert preview["format"] == "csv"
    assert preview["summary"]["affected_codes"] == ["us_cpi_yoy"]
    assert preview["rows"][0]["value"] == "3.100000"


def test_preview_market_indicator_seed_content_keeps_valid_rows_visible_when_another_row_fails():
    session = make_session()
    content = json.dumps(
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
                "source": "Audited seed: unsupported code",
                "components": {
                    "source_name": "Example source",
                    "notes": "Reviewed but unsupported indicator code.",
                },
            },
            {
                "code": "cn_m2_yoy",
                "as_of": "2026-06-30",
                "value": "8.300000",
                "source": "Audited seed: PBOC public monetary statistics",
                "components": {"source_url": "https://example.com/pboc-m2-release"},
            },
        ]
    )

    preview = preview_market_indicator_observation_seed_content(
        content,
        session=session,
    )

    assert preview["status"] == "invalid"
    assert preview["can_import"] is False
    assert preview["summary"]["valid_rows"] == 1
    assert preview["summary"]["invalid_rows"] == 2
    assert [row["status"] for row in preview["rows"]] == ["valid", "invalid", "invalid"]
    assert "unknown_macro_code" in "; ".join(preview["errors"])
    assert "components must include one of" in "; ".join(preview["errors"])
    assert session.query(MarketIndicatorObservation).count() == 0


def test_preview_market_indicator_seed_content_detects_existing_observation_update():
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
                "methodology": "Initial reviewed value.",
            },
        ),
        session=session,
    )
    content = json.dumps(
        [
            {
                "code": "us_10y_yield",
                "as_of": "2026-07-03",
                "value": "4.310000",
                "source": "Audited seed: FRED DGS10 revised",
                "components": {
                    "source_series_id": "DGS10",
                    "review_note": "Operator reviewed revised value.",
                },
            }
        ]
    )

    preview = preview_market_indicator_observation_seed_content(
        content,
        session=session,
    )

    assert preview["status"] == "valid"
    assert preview["summary"]["updates"] == 1
    assert preview["rows"][0]["intent"] == "update"
    assert get_latest_market_indicator_payload("us_10y_yield", session=session)["value"] == 4.25


def test_import_market_indicator_seed_content_requires_overwrite_acknowledgement():
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
                "methodology": "Initial reviewed value.",
            },
        ),
        session=session,
    )
    content = json.dumps(
        [
            {
                "code": "us_10y_yield",
                "as_of": "2026-07-03",
                "value": "4.310000",
                "source": "Audited seed: FRED DGS10 revised",
                "components": {
                    "source_series_id": "DGS10",
                    "review_note": "Operator reviewed revised value.",
                },
            }
        ]
    )

    with pytest.raises(MarketIndicatorSeedOverwriteRequiredError) as error:
        import_market_indicator_observation_seed_content(content, session=session)

    assert error.value.preview["summary"]["updates"] == 1
    assert get_latest_market_indicator_payload("us_10y_yield", session=session)["value"] == 4.25

    result = import_market_indicator_observation_seed_content(
        content,
        session=session,
        overwrite_acknowledged=True,
    )

    assert result["status"] == "imported"
    assert result["observations"] == 1
    assert result["summary"] == {"inserts": 0, "updates": 1}
    assert get_latest_market_indicator_payload("us_10y_yield", session=session)["value"] == 4.31
