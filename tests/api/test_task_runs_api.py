from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from apps.api.main import app
from packages.services.task_runs import fail_task_run, finish_task_run, start_task_run
from packages.shared.database import Base, get_session


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_task_runs_api_returns_recent_and_latest_task_run():
    session = make_session()
    task_run = start_task_run(
        "reports.refresh_daily_watchlist_analysis",
        {"watchlist": "AAPL:US"},
        session=session,
    )
    finish_task_run(task_run, {"item_count": 1}, session=session)

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        recent_response = client.get("/task-runs/recent", params={"limit": 1})
        latest_response = client.get(
            "/task-runs/latest",
            params={"task_name": "reports.refresh_daily_watchlist_analysis"},
        )
        detail_response = client.get(f"/task-runs/{task_run.id}")
    finally:
        app.dependency_overrides.clear()

    assert recent_response.status_code == 200
    recent = recent_response.json()
    assert recent["items"][0]["task_name"] == "reports.refresh_daily_watchlist_analysis"
    assert recent["items"][0]["status"] == "succeeded"

    assert latest_response.status_code == 200
    latest = latest_response.json()
    assert latest["task_name"] == "reports.refresh_daily_watchlist_analysis"
    assert latest["status"] == "succeeded"

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["item"]["id"] == str(task_run.id)
    assert detail["item"]["result_json"] == {"item_count": 1}


def test_task_runs_api_filters_recent_by_status():
    session = make_session()
    succeeded_run = start_task_run("reports.refresh_daily_watchlist_analysis", {}, session=session)
    finish_task_run(succeeded_run, {"item_count": 1}, session=session)
    failed_run = start_task_run("reports.refresh_daily_watchlist_analysis", {}, session=session)
    fail_task_run(failed_run, "provider timeout", session=session)

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        response = client.get("/task-runs/recent", params={"status": "failed"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    assert payload["items"][0]["status"] == "failed"


@patch("packages.services.task_dispatch.dispatch_task_run", return_value="celery-task-id-123")
def test_task_runs_api_retries_existing_task_run(mock_dispatch):
    session = make_session()
    failed_run = start_task_run(
        "reports.refresh_daily_watchlist_analysis",
        {"watchlist": "0700:HK"},
        session=session,
    )
    fail_task_run(failed_run, "provider timeout", session=session)

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        response = client.post(f"/task-runs/{failed_run.id}/retry")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "retry_started"
    assert payload["item"]["status"] == "running"
    assert payload["item"]["input_json"]["retry_of"] == str(failed_run.id)
    assert payload["celery_task_id"] == "celery-task-id-123"
    mock_dispatch.assert_called_once()
