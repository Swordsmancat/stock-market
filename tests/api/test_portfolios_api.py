from fastapi.testclient import TestClient

from apps.api.main import app
from packages.shared.database import get_session


def override_no_database_session():
    yield None


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
