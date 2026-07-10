from fastapi.testclient import TestClient

from apps.api.main import app


def test_health_endpoint_returns_ok():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_runtime_health_exposes_identity_without_connection_credentials(monkeypatch):
    from apps.api.routers import health as health_router

    monkeypatch.setattr(health_router.settings, "app_env", "acceptance")
    monkeypatch.setattr(
        health_router.settings,
        "database_url",
        "postgresql+psycopg://secret-user:secret-password@db:5432/stock_acceptance",
    )

    response = TestClient(app).get("/health/runtime")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "app_env": "acceptance",
        "database_name": "stock_acceptance",
        "celery_timezone": "Asia/Shanghai",
    }
    assert "secret" not in response.text
