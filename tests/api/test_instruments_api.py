from fastapi.testclient import TestClient

from apps.api.main import app


def test_list_instruments_returns_seed_scope():
    client = TestClient(app)
    response = client.get("/instruments")
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"][0]["symbol"] in {"600519", "0700", "AAPL"}
