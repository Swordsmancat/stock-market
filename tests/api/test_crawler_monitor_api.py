from fastapi.testclient import TestClient

from apps.api.main import app
from packages.shared.database import get_session


def _override_session():
    yield object()


def test_crawler_monitor_api_returns_allowlisted_projection(monkeypatch):
    expected = {
        "status": "ok",
        "generated_at": "2026-07-17T12:00:00+00:00",
        "summary": {
            "total": 11,
            "running": 0,
            "healthy": 0,
            "attention": 11,
            "recent_failures": 0,
        },
        "items": [],
    }
    monkeypatch.setattr(
        "apps.api.routers.crawler_monitor.get_crawler_monitor",
        lambda session: expected,
    )
    app.dependency_overrides[get_session] = _override_session
    try:
        response = TestClient(app).get("/crawler-monitor")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == expected
