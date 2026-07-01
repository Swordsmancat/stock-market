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


def test_ingestion_api_dispatches_task_run_and_writes_database(monkeypatch):
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
        ingest_response = client.post(
            "/ingestion/mock-snapshot",
            params={
                "market": "US",
                "provider": "mock",
                "start": "2026-01-01",
                "end": "2026-01-02",
            },
        )
        bars_response = client.get(
            "/market-data/AAPL/bars",
            params={"timeframe": "1d", "start": "2026-01-01", "end": "2026-01-02"},
        )
    finally:
        app.dependency_overrides.clear()

    assert ingest_response.status_code == 200
    ingest_payload = ingest_response.json()
    assert ingest_payload["status"] == "dispatched"
    task_run = ingest_payload["task_run"]
    assert task_run["task_name"] == "ingestion.ingest_market_data"
    assert task_run["status"] == "succeeded"
    result = task_run["result_json"]
    assert result["status"] == "ingested"
    assert result["market"] == "US"
    assert result["bar_count"] == 2

    assert bars_response.status_code == 200
    bars_payload = bars_response.json()
    assert bars_payload["source"] == "database"
    assert len(bars_payload["items"]) == 2
    assert bars_payload["items"][-1]["close"] == 102.0
