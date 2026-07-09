from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.routers import market_daily_data as market_daily_data_router


def test_stock_fund_flow_api_passes_query_to_service(monkeypatch):
    captured_arguments = {}

    def get_stock_fund_flow_payload_stub(
        *,
        market: str,
        window: str,
        limit: int,
        provider_name: str | None = None,
    ) -> dict[str, object]:
        captured_arguments["market"] = market
        captured_arguments["window"] = window
        captured_arguments["limit"] = limit
        captured_arguments["provider_name"] = provider_name
        return {
            "status": "ok",
            "data_mode": "delayed",
            "source": "fake_stock_fund_flow",
            "provider": provider_name,
            "requested_provider": provider_name,
            "effective_provider": provider_name,
            "as_of": "2026-07-09T09:30:00+00:00",
            "generated_at": "2026-07-09T09:31:00+00:00",
            "market": market,
            "window": window,
            "trade_date": None,
            "availability": {"status": "delayed"},
            "provider_capabilities": {"stock_fund_flow": {"status": "delayed"}},
            "message": "ok",
            "count": 1,
            "items": [{"symbol": "600519", "rank": 1}],
        }

    monkeypatch.setattr(
        market_daily_data_router,
        "get_stock_fund_flow_payload",
        get_stock_fund_flow_payload_stub,
    )
    client = TestClient(app)

    response = client.get(
        "/market-daily-data/fund-flow/stocks",
        params={"market": "CN", "window": "5d", "limit": 3, "provider": "akshare"},
    )

    assert response.status_code == 200
    assert captured_arguments == {
        "market": "CN",
        "window": "5d",
        "limit": 3,
        "provider_name": "akshare",
    }
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["items"][0]["symbol"] == "600519"


def test_limit_up_reasons_api_passes_date_alias_to_service(monkeypatch):
    captured_arguments = {}

    def get_limit_up_reasons_payload_stub(
        *,
        trade_date: str | None,
        market: str,
        limit: int,
        provider_name: str | None = None,
    ) -> dict[str, object]:
        captured_arguments["trade_date"] = trade_date
        captured_arguments["market"] = market
        captured_arguments["limit"] = limit
        captured_arguments["provider_name"] = provider_name
        return {
            "status": "degraded",
            "data_mode": "delayed",
            "source": "fake_limit_up_pool",
            "provider": provider_name,
            "requested_provider": provider_name,
            "effective_provider": provider_name,
            "as_of": "2026-07-09T09:30:00+00:00",
            "generated_at": "2026-07-09T09:31:00+00:00",
            "market": market,
            "window": "today",
            "trade_date": trade_date,
            "availability": {"status": "delayed", "reason_detail": "unavailable"},
            "provider_capabilities": {"limit_up_reasons": {"status": "unavailable"}},
            "message": "pool rows only",
            "count": 1,
            "items": [{"symbol": "002001", "rank": 1, "reason": None}],
        }

    monkeypatch.setattr(
        market_daily_data_router,
        "get_limit_up_reasons_payload",
        get_limit_up_reasons_payload_stub,
    )
    client = TestClient(app)

    response = client.get(
        "/market-daily-data/limit-up-reasons",
        params={"date": "2026-07-09", "limit": 4, "provider": "akshare"},
    )

    assert response.status_code == 200
    assert captured_arguments == {
        "trade_date": "2026-07-09",
        "market": "CN",
        "limit": 4,
        "provider_name": "akshare",
    }
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["provider_capabilities"]["limit_up_reasons"]["status"] == "unavailable"


def test_stock_fund_flow_unknown_provider_returns_unavailable_payload():
    client = TestClient(app)

    response = client.get(
        "/market-daily-data/fund-flow/stocks",
        params={"provider": "unknown_provider"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "unavailable"
    assert payload["requested_provider"] == "unknown_provider"
    assert payload["items"] == []


def test_market_daily_data_limit_validation_is_preserved():
    client = TestClient(app)

    response = client.get("/market-daily-data/fund-flow/stocks", params={"limit": 101})

    assert response.status_code == 422
