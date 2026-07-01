from fastapi.testclient import TestClient

from apps.api.main import app
from packages.shared.database import get_session


def override_no_database_session():
    yield None


def test_get_bars_returns_mock_market_data():
    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get(
            "/market-data/AAPL/bars",
            params={"timeframe": "1d", "start": "2026-01-01", "end": "2026-01-03"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["timeframe"] == "1d"
    assert len(payload["items"]) == 3
    assert payload["items"][0]["close"] == 101.0


def test_get_indicators_returns_latest_ma_and_rsi():
    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get(
            "/market-data/AAPL/indicators",
            params={"start": "2026-01-01", "end": "2026-01-15", "ma_window": 3},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["indicators"]["ma"] == 114.0
    assert 0 <= payload["indicators"]["rsi"] <= 100


def test_get_latest_bar_returns_mock_price():
    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get("/market-data/AAPL/latest", params={"provider": "mock"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["item"] is not None
    assert float(payload["item"]["close"]) > 0


def test_get_latest_bars_batch_returns_multiple_symbols():
    app.dependency_overrides[get_session] = override_no_database_session
    try:
        client = TestClient(app)
        response = client.get(
            "/market-data/latest",
            params={"symbols": "AAPL,0700", "provider": "mock"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 2
    assert payload["items"][0]["symbol"] == "AAPL"
