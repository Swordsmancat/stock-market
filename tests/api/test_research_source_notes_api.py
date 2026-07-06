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


def with_test_client(session):
    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


def test_research_source_notes_api_creates_and_lists_reviewed_note(monkeypatch):
    session = make_session()
    monkeypatch.setattr(
        "apps.api.routers.research_source_notes.clear_market_overview_cache",
        lambda provider_name=None: 3,
    )
    client = with_test_client(session)
    try:
        create_response = client.post(
            "/research-source-notes",
            json={
                "title": "Buffett Indicator source review",
                "source_name": "World Bank",
                "source_type": "valuation_component",
                "source_url": "https://example.com/gdp",
                "symbols": ["AAPL"],
                "tags": ["macro", "valuation"],
                "as_of": "2026-07-03",
                "excerpt": "Reviewed source excerpt.",
                "note": "Calculation note.",
                "source_id": "buffett_manual_valuation_components",
                "source_label": "Buffett Indicator manual valuation components",
                "source_category": "valuation",
                "target_indicator_codes": ["buffett_indicator_us"],
                "component_role": "gdp",
                "methodology_note": "Reviewed GDP component methodology.",
                "license_note": "Public source for personal research review.",
                "review_status": "reviewed",
                "is_citable": True,
            },
        )
        list_response = client.get("/research-source-notes?citable_only=true")
    finally:
        app.dependency_overrides.clear()

    assert create_response.status_code == 200
    created = create_response.json()
    assert created["title"] == "Buffett Indicator source review"
    assert created["citation_id"].startswith("research_source_note:")
    assert created["metadata"]["source_id"] == "buffett_manual_valuation_components"
    assert created["metadata"]["target_indicator_codes"] == ["buffett_indicator_us"]
    assert created["metadata"]["component_role"] == "gdp"
    assert created["metadata"]["completeness"] == {"score": 7, "total": 7, "status": "complete"}
    assert created["cache"]["market_overview_cleared"] == 3
    assert list_response.status_code == 200
    listed = list_response.json()
    assert listed["summary"]["total"] == 1
    assert listed["items"][0]["title"] == "Buffett Indicator source review"
    assert listed["items"][0]["metadata"]["source_label"] == "Buffett Indicator manual valuation components"


def test_research_source_notes_api_rejects_citable_drafts():
    session = make_session()
    client = with_test_client(session)
    try:
        response = client.post(
            "/research-source-notes",
            json={
                "title": "Draft note",
                "source_name": "Source",
                "source_type": "macro_note",
                "source_url": "https://example.com",
                "excerpt": "Draft excerpt.",
                "review_status": "draft",
                "is_citable": True,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"]["errors"] == [
        "Citable notes must have review_status=reviewed."
    ]


def test_research_source_notes_api_rejects_unsafe_source_url():
    session = make_session()
    client = with_test_client(session)
    try:
        response = client.post(
            "/research-source-notes",
            json={
                "title": "Unsafe source URL",
                "source_name": "Manual source",
                "source_type": "macro_note",
                "source_url": "data:text/html,<script>alert(1)</script>",
                "excerpt": "Reviewed excerpt.",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["detail"]["errors"] == ["source_url must use http or https."]
