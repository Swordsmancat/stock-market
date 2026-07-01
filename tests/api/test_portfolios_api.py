from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from apps.api.main import app
from packages.services.ingestion import ingest_mock_market_snapshot
from packages.shared.database import Base, get_session


def override_no_database_session():
    yield None


def make_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def make_session_without_portfolios_table():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = [
        table
        for name, table in Base.metadata.tables.items()
        if name not in {"portfolios", "portfolio_positions"}
    ]
    Base.metadata.create_all(engine, tables=tables)
    return sessionmaker(bind=engine)()


def test_get_demo_portfolio_returns_positions_and_simulated_recommendation():
    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get("/portfolios/demo")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "demo"
    assert payload["base_currency"] == "USD"
    assert payload["positions"][0]["symbol"] == "AAPL"
    assert payload["recommendation"]["status"] == "simulated"
    assert payload["recommendation"]["actions"][0]["action"] in {"hold", "rebalance"}


def test_get_demo_portfolio_falls_back_when_portfolio_tables_missing():
    session = make_session_without_portfolios_table()

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        response = client.get("/portfolios/demo")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "demo"
    assert payload["positions"][0]["symbol"] == "AAPL"
    assert payload["positions"][0]["unrealized_pnl"] is not None


def test_portfolio_crud_and_position_management():
    session = make_session()
    ingest_mock_market_snapshot("US", date(2026, 1, 1), date(2026, 1, 2), session=session)

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)

        create_response = client.post(
            "/portfolios",
            json={"name": "Growth", "base_currency": "USD"},
        )
        assert create_response.status_code == 200
        created = create_response.json()
        portfolio_id = created["id"]
        assert created["name"] == "Growth"
        assert created["positions"] == []

        list_response = client.get("/portfolios")
        assert list_response.status_code == 200
        list_payload = list_response.json()
        assert len(list_payload["items"]) >= 1

        position_response = client.post(
            f"/portfolios/{portfolio_id}/positions",
            json={
                "symbol": "MSFT",
                "market": "US",
                "quantity": 5,
                "avg_cost": 200,
                "name": "Microsoft",
            },
        )
        assert position_response.status_code == 200
        position_payload = position_response.json()
        assert len(position_payload["positions"]) == 1
        assert position_payload["positions"][0]["symbol"] == "MSFT"

        get_response = client.get(f"/portfolios/{portfolio_id}")
        assert get_response.status_code == 200
        assert get_response.json()["positions"][0]["symbol"] == "MSFT"

        patch_response = client.patch(
            f"/portfolios/{portfolio_id}",
            json={"name": "Growth Updated"},
        )
        assert patch_response.status_code == 200
        assert patch_response.json()["name"] == "Growth Updated"

        remove_response = client.delete(
            f"/portfolios/{portfolio_id}/positions",
            params={"symbol": "MSFT", "market": "US"},
        )
        assert remove_response.status_code == 200
        assert remove_response.json()["status"] == "removed"

        delete_response = client.delete(f"/portfolios/{portfolio_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["status"] == "deleted"
    finally:
        app.dependency_overrides.clear()


def test_demo_portfolio_accepts_position_upsert_by_demo_id():
    session = make_session()
    ingest_mock_market_snapshot("US", date(2026, 1, 1), date(2026, 1, 2), session=session)

    def override_session():
        yield session

    app.dependency_overrides[get_session] = override_session
    try:
        client = TestClient(app)
        response = client.post(
            "/portfolios/demo/positions",
            json={
                "symbol": "NVDA",
                "market": "US",
                "quantity": 2,
                "avg_cost": 500,
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    symbols = {position["symbol"] for position in payload["positions"]}
    assert "NVDA" in symbols
