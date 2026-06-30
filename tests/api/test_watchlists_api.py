from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from apps.api.main import app
from packages.shared.database import Base, get_session


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_watchlist_api_returns_persisted_default_items():
    session = make_session()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        response = client.get("/watchlist")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "database"
    assert payload["name"] == "default"
    assert payload["items"][0]["symbol"] == "AAPL"
    assert payload["items"][0]["alert_rules"] == {}


def test_watchlist_api_upserts_item_with_alert_rules():
    session = make_session()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        upsert_response = client.post(
            "/watchlist/items",
            json={
                "symbol": "0700",
                "market": "HK",
                "name": "Tencent Holdings",
                "alert_rules": {"price_above": 400},
            },
        )
        list_response = client.get("/watchlist")
    finally:
        app.dependency_overrides.clear()

    assert upsert_response.status_code == 200
    upsert_payload = upsert_response.json()
    assert upsert_payload["item"]["symbol"] == "0700"
    assert upsert_payload["item"]["alert_rules"] == {"price_above": 400}
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["items"] == [
        {
            "symbol": "0700",
            "market": "HK",
            "name": "Tencent Holdings",
            "is_active": True,
            "alert_rules": {"price_above": 400},
        }
    ]
