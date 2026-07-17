from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.routers import market_movers as market_movers_router


def test_market_movers_api_delegates_validated_query(monkeypatch):
    captured: dict[str, object] = {}

    def stub(**kwargs):
        captured.update(kwargs)
        return {"status": "ok", "items": []}

    monkeypatch.setattr(market_movers_router, "get_market_movers_payload", stub)
    response = TestClient(app).get(
        "/market-movers",
        params={
            "market": "CN",
            "direction": "losers",
            "exchange": "BSE",
            "limit": 50,
        },
    )

    assert response.status_code == 200
    assert captured["market"] == "CN"
    assert captured["direction"] == "losers"
    assert captured["exchange"] == "BSE"
    assert captured["limit"] == 50
    assert captured["session"] is not None


def test_market_movers_api_rejects_unsupported_queries():
    client = TestClient(app)

    assert client.get("/market-movers", params={"market": "US"}).status_code == 422
    assert client.get("/market-movers", params={"direction": "flat"}).status_code == 422
    assert client.get("/market-movers", params={"exchange": "NYSE"}).status_code == 422
    assert client.get("/market-movers", params={"limit": 25}).status_code == 422
