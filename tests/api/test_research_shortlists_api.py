from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

import packages.domain.models  # noqa: F401
from apps.api.main import app
from apps.api.routers import research_shortlists as shortlist_router
from packages.services.research_shortlists import ResearchShortlistReadinessError
from packages.shared.database import Base, get_session


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_generate_shortlist_forwards_compatible_request_fields(monkeypatch):
    session = make_session()
    captured = {}

    def override_session():
        yield session

    def generate(payload, *, session):
        captured["payload"] = payload
        captured["session"] = session
        return {
            "status": "ok",
            "run": {"id": "run-1", "research_signal_only": True},
            "items": [],
            "research_signal_only": True,
            "safety": {"no_automated_trading": True},
        }

    app.dependency_overrides[get_session] = override_session
    monkeypatch.setattr(shortlist_router, "generate_research_shortlist", generate)
    try:
        response = TestClient(app).post(
            "/research-shortlists/generate",
            json={
                "profile_id": "quality_value",
                "overrides": {"max_pe_ratio": 18},
                "market": "CN",
                "asset_type": "stock",
                "shortlist_limit": 5,
                "locale": "en",
                "use_llm": False,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["research_signal_only"] is True
    assert captured["payload"].profile_id == "quality_value"
    assert captured["payload"].overrides == {"max_pe_ratio": 18.0}
    assert captured["payload"].shortlist_limit == 5
    assert captured["payload"].locale == "en"
    assert captured["payload"].use_llm is False
    assert captured["session"] is session


def test_generate_shortlist_maps_validation_and_readiness_errors(monkeypatch):
    session = make_session()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        monkeypatch.setattr(
            shortlist_router,
            "generate_research_shortlist",
            lambda *_, **__: (_ for _ in ()).throw(ValueError("Unknown profile")),
        )
        invalid = TestClient(app).post(
            "/research-shortlists/generate",
            json={"profile_id": "missing"},
        )
        assert invalid.status_code == 400
        assert invalid.json()["detail"] == "Unknown profile"

        monkeypatch.setattr(
            shortlist_router,
            "generate_research_shortlist",
            lambda *_, **__: (_ for _ in ()).throw(
                ResearchShortlistReadinessError(
                    "EVIDENCE_COVERAGE_NOT_READY",
                    "Coverage is not ready.",
                    details={"coverage": {"status": "needs_attention"}},
                )
            ),
        )
        conflict = TestClient(app).post(
            "/research-shortlists/generate",
            json={"profile_id": "quality_value"},
        )
    finally:
        app.dependency_overrides.clear()

    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "EVIDENCE_COVERAGE_NOT_READY"
    assert conflict.json()["detail"]["details"]["coverage"]["status"] == "needs_attention"


def test_generate_shortlist_rejects_invalid_override_as_bad_request():
    session = make_session()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        response = TestClient(app).post(
            "/research-shortlists/generate",
            json={
                "profile_id": "quality_value",
                "overrides": {"min_rsi": 101},
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert "min_rsi" in response.json()["detail"]

    app.dependency_overrides[get_session] = override_session
    try:
        unsupported = TestClient(app).post(
            "/research-shortlists/generate",
            json={
                "profile_id": "quality_value",
                "overrides": {"invented_rule": 1},
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert unsupported.status_code == 400
    assert "invented_rule" in unsupported.json()["detail"]


def test_latest_no_data_and_missing_detail_are_explicit(monkeypatch):
    session = make_session()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    monkeypatch.setattr(
        shortlist_router,
        "get_latest_research_shortlist",
        lambda **_: {
            "status": "no_data",
            "run": None,
            "items": [],
            "research_signal_only": True,
            "safety": {"no_automated_trading": True},
        },
    )
    monkeypatch.setattr(shortlist_router, "get_research_shortlist", lambda *_, **__: None)
    try:
        latest = TestClient(app).get(
            "/research-shortlists/latest?market=CN&profile_id=balanced_research"
        )
        missing = TestClient(app).get(f"/research-shortlists/{uuid4()}")
    finally:
        app.dependency_overrides.clear()

    assert latest.status_code == 200
    assert latest.json() == {
        "status": "no_data",
        "run": None,
        "items": [],
        "research_signal_only": True,
        "safety": {"no_automated_trading": True},
    }
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Research shortlist not found"
