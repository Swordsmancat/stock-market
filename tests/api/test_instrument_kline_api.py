from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.routers import instrument_kline as instrument_kline_router


def test_instrument_kline_api_delegates_normalized_query(monkeypatch):
    captured: dict[str, object] = {}

    def stub(**kwargs):
        captured.update(kwargs)
        return {"status": "ready", "catalog": []}

    monkeypatch.setattr(
        instrument_kline_router,
        "get_instrument_kline_payload",
        stub,
    )
    response = TestClient(app).get(
        "/instrument-kline",
        params={
            "q": "300",
            "asset_type": "etf",
            "symbol": "510300",
            "market": "CN",
            "period": "6m",
            "limit": 12,
            "offset": 24,
        },
    )

    assert response.status_code == 200
    assert captured["query"] == "300"
    assert captured["asset_type"] == "etf"
    assert captured["symbol"] == "510300"
    assert captured["market"] == "CN"
    assert captured["period"] == "6m"
    assert captured["limit"] == 12
    assert captured["offset"] == 24
    assert captured["session"] is not None


def test_instrument_kline_api_rejects_invalid_queries():
    client = TestClient(app)

    assert client.get("/instrument-kline", params={"asset_type": "future"}).status_code == 422
    assert client.get("/instrument-kline", params={"period": "5y"}).status_code == 422
    assert client.get("/instrument-kline", params={"limit": 51}).status_code == 422
    assert client.get("/instrument-kline", params={"offset": -1}).status_code == 422
    assert client.get("/instrument-kline", params={"symbol": "510300"}).status_code == 422
