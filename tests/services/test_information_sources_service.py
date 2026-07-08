from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.domain.models import GeneratedReport, NewsArticle
from packages.services.information_sources import get_information_source_readiness_payload
from packages.services.market_indicators import (
    MarketIndicatorObservationSeed,
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


def _item_by_id(payload: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(item["id"]): item for item in payload["items"]}


def test_information_source_readiness_returns_no_data_registry():
    session = make_session()

    payload = get_information_source_readiness_payload(session=session)
    items = _item_by_id(payload)
    statuses = {item["status"] for item in items.values()}

    assert set(payload) == {
        "status",
        "summary",
        "groups",
        "items",
        "diagnostics",
        "source_capabilities",
    }
    assert statuses >= {"needs_adapter", "needs_manual_seed", "no_data", "future"}
    assert payload["summary"]["total"] == 11
    assert payload["summary"]["configured"] == 0
    assert payload["summary"]["needs_action"] == 9
    assert payload["summary"]["future"] == 2
    assert items["fred_us_rates"]["coverage"] == ["DGS10", "DGS2", "T10Y2Y"]
    assert items["pboc_cn_m2_public_manual"]["status"] == "needs_manual_seed"
    assert items["world_bank_buffett_indicator"]["status"] == "needs_adapter"
    assert items["generated_reports"]["status"] == "no_data"
    assert items["stored_news"]["status"] == "no_data"
    assert items["social_sentiment_future"]["status"] == "future"
    assert items["sec_filings_future_documents"]["status"] == "future"
    assert all(
        required_key in item
        for item in items.values()
        for required_key in (
            "id",
            "label",
            "category",
            "authority",
            "status",
            "freshness_policy",
            "ai_usage",
            "next_action",
            "collection_note",
            "citation_policy",
            "seed_template",
            "collection_links",
            "evidence_count",
            "latest_as_of",
            "coverage",
        )
    )
    assert {group["category"] for group in payload["groups"]} >= {
        "macro",
        "valuation",
        "reports",
        "news",
        "sentiment",
        "documents",
        "manual_seed",
    }
    assert {diagnostic["severity"] for diagnostic in payload["diagnostics"]} == {
        "info",
        "warning",
    }
    assert payload["source_capabilities"]["summary"]["total"] >= 6
    assert payload["source_capabilities"]["citation_policy"].startswith(
        "Capability metadata is not evidence"
    )


def test_information_source_readiness_includes_official_macro_collection_links():
    session = make_session()

    payload = get_information_source_readiness_payload(session=session)
    fred_rates = _item_by_id(payload)["fred_us_rates"]

    assert fred_rates["status"] == "needs_adapter"
    assert fred_rates["collection_note"] == (
        "Collect DGS10, DGS2, and T10Y2Y observations from FRED, then "
        "store reviewed values with source URLs and methodology notes."
    )
    assert fred_rates["citation_policy"] == (
        "FRED links are collection guidance only; AI may cite rates after "
        "reviewed observations are stored locally."
    )
    assert {
        (str(link["label"]), str(link["url"]), str(link["source_type"]))
        for link in fred_rates["collection_links"]
    } >= {
        (
            "FRED DGS10",
            "https://fred.stlouisfed.org/series/DGS10",
            "official_series",
        ),
        (
            "FRED DGS2",
            "https://fred.stlouisfed.org/series/DGS2",
            "official_series",
        ),
        (
            "FRED T10Y2Y",
            "https://fred.stlouisfed.org/series/T10Y2Y",
            "official_series",
        ),
    }


def test_information_source_readiness_includes_fred_rates_seed_template():
    session = make_session()

    payload = get_information_source_readiness_payload(session=session)
    fred_rates = _item_by_id(payload)["fred_us_rates"]
    seed_template = fred_rates["seed_template"]

    assert fred_rates["status"] == "needs_adapter"
    assert fred_rates["evidence_count"] == 0
    assert seed_template["label"] == "FRED rates seed template"
    assert seed_template["target_indicator_codes"] == [
        "us_10y_yield",
        "us_2y_yield",
        "us_10y_2y_spread",
    ]
    assert seed_template["required_fields"] == [
        "code",
        "as_of",
        "value",
        "source",
        "components",
    ]
    assert seed_template["import_command"] == (
        "python scripts/import_market_indicator_seeds.py path/to/macro-seeds.json"
    )
    assert seed_template["json_template"]["observations"][0] == {
        "code": "us_10y_yield",
        "as_of": "YYYY-MM-DD",
        "value": "<reviewed decimal>",
        "source": "Audited seed: FRED DGS10",
        "components": {
            "source_series_id": "DGS10",
            "source_url": "https://fred.stlouisfed.org/series/DGS10",
            "methodology": "<operator review note>",
        },
    }
    assert seed_template["csv_header"] == [
        "code",
        "as_of",
        "value",
        "source",
        "components_json",
    ]
    assert "us_10y_yield,YYYY-MM-DD,<reviewed decimal>" in seed_template[
        "csv_example_rows"
    ][0]
    assert '""source_series_id"": ""DGS10""' in seed_template["csv_example_rows"][0]
    assert {
        item["id"]
        for item in seed_template["review_checklist"]
        if item["required"] is True
    } >= {"replace_placeholders", "preserve_source_reference", "record_method"}
    assert seed_template["warnings"] == [
        "Replace every placeholder before import; template values are not market data.",
        "Do not treat source links or template rows as AI citations.",
    ]
    assert seed_template["citation_boundary"].startswith("This template is not evidence")


def test_information_source_readiness_includes_buffett_collection_guidance():
    session = make_session()

    payload = get_information_source_readiness_payload(session=session)
    buffett_components = _item_by_id(payload)["buffett_manual_valuation_components"]

    assert buffett_components["status"] == "needs_manual_seed"
    assert buffett_components["collection_note"] == (
        "Collect market-cap and GDP components from reviewed public "
        "sources, calculate the ratio, and store the component URLs."
    )
    assert buffett_components["citation_policy"] == (
        "Buffett Indicator ratios are citeable only after each component "
        "and calculation method are stored locally."
    )
    assert {
        (str(link["label"]), str(link["url"]))
        for link in buffett_components["collection_links"]
    } == {
        (
            "World Bank market cap / GDP",
            "https://data.worldbank.org/indicator/CM.MKT.LCAP.GD.ZS",
        ),
        (
            "World Bank GDP",
            "https://data.worldbank.org/indicator/NY.GDP.MKTP.CD",
        ),
    }
    seed_template = buffett_components["seed_template"]
    assert seed_template["label"] == "Buffett Indicator component seed template"
    assert seed_template["target_indicator_codes"] == [
        "buffett_indicator_cn",
        "buffett_indicator_hk",
        "buffett_indicator_us",
    ]
    assert seed_template["json_template"]["observations"][0]["components"][
        "calculation"
    ] == "<market capitalization divided by GDP calculation>"
    assert any(
        item["id"] == "review_components"
        for item in seed_template["review_checklist"]
    )
    assert seed_template["citation_boundary"].startswith("This template is not evidence")


def test_information_source_readiness_includes_world_bank_buffett_adapter_guidance():
    session = make_session()

    payload = get_information_source_readiness_payload(session=session)
    world_bank = _item_by_id(payload)["world_bank_buffett_indicator"]

    assert world_bank["status"] == "needs_adapter"
    assert world_bank["authority"] == "World Bank public indicators API"
    assert world_bank["collection_note"] == (
        "Use the World Bank API adapter to fetch market capitalization as "
        "percent of GDP and same-year GDP context for supported regions."
    )
    assert world_bank["citation_policy"] == (
        "World Bank links and adapter diagnostics are guidance only; AI may "
        "cite Buffett Indicator values after validated observations are "
        "stored locally."
    )
    assert world_bank["coverage"] == [
        "CM.MKT.LCAP.GD.ZS",
        "NY.GDP.MKTP.CD",
        "buffett_indicator_cn",
        "buffett_indicator_hk",
        "buffett_indicator_us",
    ]
    assert {
        (str(link["label"]), str(link["url"]))
        for link in world_bank["collection_links"]
    } == {
        (
            "World Bank market cap / GDP",
            "https://data.worldbank.org/indicator/CM.MKT.LCAP.GD.ZS",
        ),
        (
            "World Bank GDP",
            "https://data.worldbank.org/indicator/NY.GDP.MKTP.CD",
        ),
    }
    assert world_bank["seed_template"] is None


def test_information_source_readiness_includes_generic_user_seed_template():
    session = make_session()

    payload = get_information_source_readiness_payload(session=session)
    user_seed_files = _item_by_id(payload)["user_seed_files"]
    seed_template = user_seed_files["seed_template"]

    assert user_seed_files["status"] == "needs_manual_seed"
    assert seed_template["label"] == "Generic audited macro seed template"
    assert "cn_m2_yoy" in seed_template["target_indicator_codes"]
    assert seed_template["json_template"]["observations"][0]["code"] == "<indicator_code>"
    assert seed_template["json_template"]["observations"][0]["components"] == {
        "source_url": "<official or reviewed source URL>",
        "methodology": "<operator review note>",
    }
    assert seed_template["import_command"] == (
        "python scripts/import_market_indicator_seeds.py path/to/macro-seeds.json"
    )


def test_information_source_readiness_keeps_future_documents_not_citeable():
    session = make_session()

    payload = get_information_source_readiness_payload(session=session)
    sec_documents = _item_by_id(payload)["sec_filings_future_documents"]

    assert sec_documents["status"] == "future"
    assert sec_documents["citation_policy"] == (
        "Future filings, announcements, and transcripts are not citeable "
        "until ingestion, licensing, and citation metadata are implemented."
    )
    assert {
        (str(link["label"]), str(link["url"]), str(link["source_type"]))
        for link in sec_documents["collection_links"]
    } == {
        (
            "SEC search filings",
            "https://www.sec.gov/search-filings",
            "official_search",
        ),
        (
            "SEC EDGAR full text",
            "https://www.sec.gov/edgar/search/",
            "official_search",
        ),
    }


def test_information_source_readiness_keeps_social_sentiment_separate_from_news():
    session = make_session()

    payload = get_information_source_readiness_payload(session=session)
    social_sentiment = _item_by_id(payload)["social_sentiment_future"]

    assert social_sentiment["status"] == "future"
    assert social_sentiment["category"] == "sentiment"
    assert social_sentiment["coverage"] == [
        "public_opinion",
        "social_results",
        "sentiment_signal_candidates",
    ]
    assert social_sentiment["citation_policy"] == (
        "Social sentiment is lower-strength context, not verified news; it is "
        "not AI-citable until reviewed local evidence storage exists."
    )
    assert "official APIs" in social_sentiment["collection_note"]


def test_information_source_readiness_marks_report_and_news_sources_configured():
    session = make_session()
    session.add(
        GeneratedReport(
            symbol="AAPL",
            report_type="stock_daily",
            as_of=date(2026, 7, 2),
            content_markdown="AAPL daily research report.",
            citations=["bars_1d:AAPL:2026-07-02"],
            source_summary={"source": "mock"},
        )
    )
    session.add(
        NewsArticle(
            symbol="AAPL",
            title="Apple reports strong growth in services revenue",
            url="https://example.com/aapl-services-growth",
            source="mock_news",
            published_at=datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc),
            summary="Apple reports strong growth and record services profit in the quarter.",
            dedupe_hash="aapl-services-growth",
        )
    )
    session.commit()

    payload = get_information_source_readiness_payload(session=session)
    items = _item_by_id(payload)
    diagnostic_item_ids = {diagnostic["item_id"] for diagnostic in payload["diagnostics"]}

    assert items["generated_reports"]["status"] == "configured"
    assert items["generated_reports"]["evidence_count"] == 1
    assert items["generated_reports"]["latest_as_of"] == "2026-07-02"
    assert items["stored_news"]["status"] == "configured"
    assert items["stored_news"]["evidence_count"] == 1
    assert items["stored_news"]["latest_as_of"] == "2026-07-02T12:00:00"
    assert payload["summary"]["configured"] == 2
    assert "generated_reports" not in diagnostic_item_ids
    assert "stored_news" not in diagnostic_item_ids


def test_information_source_readiness_marks_macro_observation_source_configured():
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
            },
        ),
        session=session,
    )

    payload = get_information_source_readiness_payload(session=session)
    items = _item_by_id(payload)

    assert items["fred_us_rates"]["status"] == "configured"
    assert items["fred_us_rates"]["evidence_count"] == 1
    assert items["fred_us_rates"]["latest_as_of"] == "2026-07-03"
    assert items["fred_us_rates"]["coverage"] == ["DGS10", "DGS2", "T10Y2Y"]
    assert items["fred_us_inflation"]["status"] == "needs_adapter"
    assert items["pboc_cn_m2_public_manual"]["status"] == "needs_manual_seed"
    assert payload["summary"]["configured"] == 2


def test_information_source_readiness_marks_world_bank_buffett_source_configured():
    session = make_session()
    seed_market_indicators(session=session)
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

    payload = get_information_source_readiness_payload(session=session)
    items = _item_by_id(payload)

    assert items["world_bank_buffett_indicator"]["status"] == "configured"
    assert items["world_bank_buffett_indicator"]["evidence_count"] == 1
    assert items["world_bank_buffett_indicator"]["latest_as_of"] == "2024-12-31"
    assert items["buffett_manual_valuation_components"]["status"] == "configured"
