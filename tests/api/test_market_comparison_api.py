from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.routers import market_comparison as market_comparison_router


def test_market_comparison_api_delegates_normalized_query(monkeypatch):
    captured: dict[str, object] = {}

    def stub(**kwargs):
        captured.update(kwargs)
        return {"status": "ok", "items": []}

    monkeypatch.setattr(
        market_comparison_router,
        "get_market_comparison_payload",
        stub,
    )
    response = TestClient(app).get(
        "/market-comparison",
        params={
            "market": "CN",
            "symbols": "600001,600002",
            "period": "6m",
            "q": "bank",
            "search_limit": 6,
        },
    )

    assert response.status_code == 200
    assert captured["symbols"] == ("600001", "600002")
    assert captured["period"] == "6m"
    assert captured["query"] == "bank"
    assert captured["search_limit"] == 6
    assert captured["session"] is not None


def test_market_comparison_api_rejects_unsupported_queries():
    client = TestClient(app)

    assert client.get("/market-comparison", params={"market": "US"}).status_code == 422
    assert client.get("/market-comparison", params={"period": "5y"}).status_code == 422
    assert client.get("/market-comparison", params={"search_limit": 20}).status_code == 422
    assert client.get(
        "/market-comparison",
        params={"symbols": "1,2,3,4,5"},
    ).status_code == 422
