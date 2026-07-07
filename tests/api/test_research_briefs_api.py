from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

import packages.domain.models  # noqa: F401
from apps.api.main import app
from packages.services import research_briefs
from packages.shared.database import Base, get_session


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def market_overview_fixture() -> dict[str, object]:
    return {
        "generated_at": "2026-07-07T01:02:03+00:00",
        "provider": "mock",
        "dashboard_brief": {
            "status": "ok",
            "generated_at": "2026-07-07T01:02:03+00:00",
            "sections": [{"id": "what_changed", "title": "What changed", "items": ["Macro evidence ready."]}],
            "citations": [
                {
                    "id": "market_indicator:us_10y_yield:2026-07-01",
                    "label": "US 10Y yield",
                    "source": "market_indicators",
                    "source_type": "macro_indicator",
                    "as_of": "2026-07-01",
                }
            ],
            "diagnostics": [],
        },
        "information_sources": {"items": []},
        "research_follow_up_queue": {"summary": {"total": 0}, "items": [], "diagnostics": []},
    }


def test_research_briefs_api_generates_and_lists_saved_briefs(monkeypatch):
    session = make_session()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    monkeypatch.setattr(research_briefs, "get_market_overview_payload", lambda **_: market_overview_fixture())
    monkeypatch.setattr(
        research_briefs,
        "get_platform_settings",
        lambda: {"llm_provider": "mock", "llm_api_key": "", "llm_api_base": ""},
    )

    try:
        client = TestClient(app)
        generated = client.post(
            "/research-briefs/generate",
            json={"provider": "mock", "locale": "en", "title": "Morning evidence brief"},
        )
        assert generated.status_code == 200
        generated_payload = generated.json()
        assert generated_payload["status"] == "stored"
        assert generated_payload["title"] == "Morning evidence brief"
        assert generated_payload["citations"][0]["id"] == "market_indicator:us_10y_yield:2026-07-01"

        listed = client.get("/research-briefs?limit=10")
        assert listed.status_code == 200
        list_payload = listed.json()
        assert list_payload["summary"] == {"total": 1, "returned": 1}
        assert list_payload["items"][0]["id"] == generated_payload["id"]
    finally:
        app.dependency_overrides.clear()
