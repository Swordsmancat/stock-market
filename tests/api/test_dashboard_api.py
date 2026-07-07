from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from apps.api.main import app
from packages.shared.database import Base, get_session


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_dashboard_market_overview_api_returns_aggregated_payload(monkeypatch):
    session = make_session()
    monkeypatch.setattr(
        "packages.services.market_dashboard.get_platform_settings",
        lambda: {
            "market_data_provider": "mock",
            "llm_provider": "mock",
            "llm_api_key": "",
            "llm_api_base": "https://api.openai.com/v1",
        },
    )

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        response = client.get("/dashboard/market-overview", params={"provider": "mock"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "mock"
    assert payload["range"]["timeframe"] == "1d"
    assert payload["followed"]["limit"] == 6
    assert payload["followed"]["items"][0]["symbol"] == "AAPL"
    assert len(payload["indices"]["items"]) == 10
    assert payload["indices"]["items"][0]["code"] == "cn_shanghai_composite"
    assert len(payload["valuation_indicators"]["items"]) == 9
    assert len(payload["macro_indicators"]["items"]) == 9
    assert payload["valuation_indicators"]["items"][0]["code"] == "buffett_indicator_cn"
    assert payload["information_sources"]["status"] == "degraded"
    assert payload["information_sources"]["summary"]["total"] == 10
    first_source = payload["information_sources"]["items"][0]
    assert first_source["id"] == "fred_us_rates"
    assert first_source["collection_note"].startswith("Collect DGS10")
    assert first_source["citation_policy"].startswith("FRED links are collection guidance")
    assert first_source["collection_links"][0] == {
        "label": "FRED DGS10",
        "url": "https://fred.stlouisfed.org/series/DGS10",
        "source_type": "official_series",
    }
    assert first_source["seed_template"]["label"] == "FRED rates seed template"
    assert first_source["seed_template"]["target_indicator_codes"] == [
        "us_10y_yield",
        "us_2y_yield",
        "us_10y_2y_spread",
    ]
    assert first_source["seed_template"]["json_template"]["observations"][0][
        "value"
    ] == "<reviewed decimal>"
    assert payload["dashboard_brief"]["status"] == "degraded"
    assert payload["dashboard_brief"]["sections"][0]["id"] == "what_changed"
    assert {
        citation["id"]
        for citation in payload["dashboard_brief"]["citations"]
    }.isdisjoint({"fred_us_rates", "seed_template:fred_us_rates"})
    assert payload["dashboard_brief"]["narrative"]["model"]["used_llm"] is False
    assert payload["dashboard_brief"]["narrative"]["context"]["source_mix"][
        "information_source_gaps"
    ] == 10
    follow_up_queue = payload["research_follow_up_queue"]
    assert follow_up_queue["summary"]["source_gap"] == 10
    assert follow_up_queue["summary"]["guidance_only"] >= 9
    assert follow_up_queue["safety"]["citations_require_reviewed_citable_notes"] is True
    assert {
        item.get("citation_id")
        for item in follow_up_queue["items"]
        if item["kind"] in {"source_gap", "seed_prep"}
    } == {None}
