from fastapi.testclient import TestClient

from apps.api.main import app


def test_get_bars_returns_mock_market_data():
    client = TestClient(app)
    response = client.get(
        "/market-data/AAPL/bars",
        params={"timeframe": "1d", "start": "2026-01-01", "end": "2026-01-03"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["timeframe"] == "1d"
    assert len(payload["items"]) == 3
    assert payload["items"][0]["close"] == 101.0


def test_get_indicators_returns_latest_ma_and_rsi():
    client = TestClient(app)
    response = client.get(
        "/market-data/AAPL/indicators",
        params={"start": "2026-01-01", "end": "2026-01-15", "ma_window": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["indicators"]["ma"] == 114.0
    assert 0 <= payload["indicators"]["rsi"] <= 100
