from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

import packages.domain.models  # noqa: F401
from apps.api.main import app
from apps.api.routers import research_shortlists as shortlist_router
from packages.shared.database import Base, get_session


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def outcome_payload(run_id: str = "run-1") -> dict[str, object]:
    return {
        "status": "ok",
        "as_of": "2026-07-12",
        "run": {
            "id": run_id,
            "decision_date": "2026-07-01",
            "market": "CN",
            "profile_id": "balanced_research",
        },
        "items": [],
        "summaries": [],
        "research_signal_only": True,
        "safety": {"no_automated_trading": True},
    }


def test_tracking_static_route_precedes_dynamic_detail_route(monkeypatch):
    session = make_session()
    captured = {}

    def override_session():
        yield session

    def tracking(**kwargs):
        captured.update(kwargs)
        return {
            "status": "no_data",
            "latest": None,
            "history": [],
            "limit": kwargs["limit"],
            "offset": kwargs["offset"],
            "research_signal_only": True,
        }

    app.dependency_overrides[get_session] = override_session
    monkeypatch.setattr(
        shortlist_router,
        "get_research_shortlist_outcome_tracking",
        tracking,
    )
    try:
        response = TestClient(app).get(
            "/research-shortlists/tracking"
            "?market=CN&profile_id=balanced_research&limit=5&offset=2"
            "&as_of=2026-07-10"
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "no_data"
    assert captured == {
        "session": session,
        "market": "CN",
        "profile_id": "balanced_research",
        "limit": 5,
        "offset": 2,
        "as_of": date(2026, 7, 10),
    }


def test_outcome_detail_and_evaluation_forward_only_public_cutoff(monkeypatch):
    session = make_session()
    captured = {}

    def override_session():
        yield session

    def read(run_id, **kwargs):
        captured["read"] = (run_id, kwargs)
        return outcome_payload(run_id)

    def evaluate(run_id, **kwargs):
        captured["evaluate"] = (run_id, kwargs)
        return outcome_payload(run_id)

    app.dependency_overrides[get_session] = override_session
    monkeypatch.setattr(shortlist_router, "get_research_shortlist_outcomes", read)
    monkeypatch.setattr(
        shortlist_router,
        "evaluate_research_shortlist_outcomes",
        evaluate,
    )
    try:
        detail = TestClient(app).get("/research-shortlists/run-1/outcomes?as_of=2026-07-10")
        evaluated = TestClient(app).post(
            "/research-shortlists/run-1/outcomes/evaluate",
            json={"as_of": "2026-07-10"},
        )
        forbidden_watermark = TestClient(app).post(
            "/research-shortlists/run-1/outcomes/evaluate",
            json={"verified_completed_through": "2026-07-10"},
        )
    finally:
        app.dependency_overrides.clear()

    assert detail.status_code == 200
    assert evaluated.status_code == 200
    assert forbidden_watermark.status_code == 422
    assert captured["read"] == (
        "run-1",
        {"session": session, "as_of": date(2026, 7, 10)},
    )
    assert captured["evaluate"] == (
        "run-1",
        {"session": session, "as_of": date(2026, 7, 10)},
    )


def test_outcome_routes_map_missing_and_cutoff_errors(monkeypatch):
    session = make_session()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    monkeypatch.setattr(
        shortlist_router,
        "get_research_shortlist_outcomes",
        lambda *_, **__: None,
    )
    monkeypatch.setattr(
        shortlist_router,
        "evaluate_research_shortlist_outcomes",
        lambda *_, **__: (_ for _ in ()).throw(ValueError("future cutoff")),
    )
    try:
        missing = TestClient(app).get("/research-shortlists/missing/outcomes")
        invalid = TestClient(app).post(
            "/research-shortlists/run-1/outcomes/evaluate",
            json={"as_of": "2026-07-31"},
        )
        invalid_limit = TestClient(app).get("/research-shortlists/tracking?limit=51")
    finally:
        app.dependency_overrides.clear()

    assert missing.status_code == 404
    assert invalid.status_code == 400
    assert invalid.json()["detail"] == "future cutoff"
    assert invalid_limit.status_code == 422
