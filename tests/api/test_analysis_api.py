from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from apps.api.main import app
from packages.shared.database import Base, get_session
from tests.helpers.celery_sync import dispatch_task_run_sync


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_analysis_refresh_dispatches_task_run_and_stores_report(monkeypatch):
    session = make_session()
    monkeypatch.setattr(
        "packages.services.task_dispatch.dispatch_task_run",
        lambda task_name, input_json, task_run_id: dispatch_task_run_sync(
            task_name,
            input_json,
            task_run_id,
            session,
        ),
    )

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        response = client.post(
            "/analysis/refresh",
            params={
                "symbol": "AAPL",
                "market": "US",
                "start": "2026-01-01",
                "end": "2026-01-20",
                "ma_window": 3,
            },
        )
        latest_response = client.get("/reports/AAPL/daily/latest")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "dispatched"
    task_run = payload["task_run"]
    assert task_run["task_name"] == "reports.refresh_daily_stock_analysis"
    assert task_run["status"] == "succeeded"
    assert task_run["celery_task_id"] == "sync-celery-id"

    result = task_run["result_json"]
    assert result["symbol"] == "AAPL"
    assert result["status"] == "refreshed"
    assert result["ingestion"]["bar_count"] == 20
    assert "MA 119.00" in result["report"]["content_markdown"]

    assert latest_response.status_code == 200
    latest = latest_response.json()
    assert latest["symbol"] == "AAPL"
    assert latest["as_of"] == "2026-01-20"
