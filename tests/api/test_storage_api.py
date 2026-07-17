from fastapi.testclient import TestClient

from apps.api.main import app
from packages.services.storage_overview import StorageOverviewUnavailable
from packages.shared.database import get_session


def _override_session():
    yield object()


def test_storage_overview_api_returns_service_projection(monkeypatch):
    monkeypatch.setattr(
        "apps.api.routers.storage.get_storage_overview",
        lambda session: {
            "status": "ok",
            "engine": "PostgreSQL",
            "row_count_kind": "estimated",
            "collected_at": "2026-07-17T10:00:00+00:00",
            "summary": {"table_count": 0, "estimated_rows": 0},
            "domains": [],
        },
    )
    app.dependency_overrides[get_session] = _override_session
    try:
        response = TestClient(app).get("/storage/overview")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["engine"] == "PostgreSQL"


def test_storage_overview_api_sanitizes_catalog_failures(monkeypatch):
    monkeypatch.setattr(
        "apps.api.routers.storage.get_storage_overview",
        lambda session: (_ for _ in ()).throw(
            StorageOverviewUnavailable("postgresql://secret@database/internal")
        ),
    )
    app.dependency_overrides[get_session] = _override_session
    try:
        response = TestClient(app).get("/storage/overview")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    assert response.json()["detail"] == {
        "status": "error",
        "message": "Database storage statistics are unavailable.",
    }
    assert "secret" not in response.text
