from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from apps.api.main import app
from packages.services.ingestion import ingest_mock_market_snapshot
from packages.shared.database import Base, get_session


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_list_instruments_returns_seed_scope():
    def override_session():
        yield None

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        response = client.get("/instruments")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "seed"
    symbols = {item["symbol"] for item in payload["items"]}
    assert symbols == {"600519", "0700", "AAPL"}


def test_list_instruments_reads_database_and_filters_results():
    session = make_session()
    ingest_mock_market_snapshot("US", date(2026, 1, 1), date(2026, 1, 2), session=session)

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        response = client.get("/instruments", params={"q": "apple", "market": "US"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "database"
    assert payload["items"] == [
        {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "market": "US",
            "exchange": "",
            "asset_type": "stock",
            "currency": "USD",
            "source": "database",
        }
    ]
