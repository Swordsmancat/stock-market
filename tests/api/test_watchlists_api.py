from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from apps.api.main import app
from packages.domain.models import AlertTrigger, Watchlist, WatchlistItem
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
    assert len(list_payload["items"]) == 1
    item = list_payload["items"][0]
    assert item["symbol"] == "0700"
    assert item["market"] == "HK"
    assert item["name"] == "Tencent Holdings"
    assert item["is_active"] is True
    assert item["alert_rules"] == {"price_above": 400}
    assert "alert_status" in item


def test_watchlist_api_removes_item_from_active_list():
    session = make_session()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        upsert_response = client.post(
            "/watchlist/items",
            json={"symbol": "AAPL", "market": "US", "name": "Apple Inc."},
        )
        remove_response = client.delete(
            "/watchlist/items",
            params={"symbol": "AAPL", "market": "US"},
        )
        list_response = client.get("/watchlist")
    finally:
        app.dependency_overrides.clear()

    assert upsert_response.status_code == 200
    assert remove_response.status_code == 200
    assert remove_response.json()["status"] == "removed"
    assert list_response.status_code == 200
    assert list_response.json()["items"] == []


def test_watchlist_membership_api_is_read_only_when_default_list_is_absent():
    session = make_session()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        response = TestClient(app).get(
            "/watchlist/items",
            params={"symbol": "AAPL", "market": "US"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "not_watched"
    assert session.query(Watchlist).count() == 0
    assert session.query(WatchlistItem).count() == 0
    assert session.query(AlertTrigger).count() == 0


def test_watchlist_membership_api_returns_exact_active_identity():
    session = make_session()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        client.post(
            "/watchlist/items",
            json={"symbol": "0700", "market": "HK", "name": "Tencent Holdings"},
        )
        watched = client.get(
            "/watchlist/items",
            params={"symbol": "0700", "market": "HK"},
        )
        other_market = client.get(
            "/watchlist/items",
            params={"symbol": "0700", "market": "US"},
        )
    finally:
        app.dependency_overrides.clear()

    assert watched.status_code == 200
    assert watched.json()["status"] == "watched"
    assert watched.json()["item"]["name"] == "Tencent Holdings"
    assert other_market.status_code == 200
    assert other_market.json()["status"] == "not_watched"


def test_watchlist_membership_api_rejects_blank_identity_as_client_error():
    session = make_session()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        response = TestClient(app).get(
            "/watchlist/items",
            params={"symbol": " ", "market": "US"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 400
    assert response.json() == {"detail": "Symbol and market are required."}
