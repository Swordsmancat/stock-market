from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from apps.api.main import app
from packages.providers.base import ProviderFundFlow
from packages.providers.base import ProviderMarketDepthSnapshot
from packages.providers.base import ProviderOrderBookLevel
from packages.providers.base import ProviderRecentTrade
from packages.services import market_data as market_data_service


def test_get_market_depth_returns_verified_provider_sections(monkeypatch):
    class FakeDepthProvider:
        def fetch_instruments(self, market: str, exchange: str | None = None) -> list:
            return []

        def fetch_bars(self, symbol: str, timeframe: str, start, end) -> list:
            raise AssertionError("Daily bars must not be used for market depth")

        def fetch_market_depth(self, symbol: str, depth_levels: int) -> ProviderMarketDepthSnapshot:
            return ProviderMarketDepthSnapshot(
                provider="fake_depth",
                source="provider",
                as_of=datetime(2026, 7, 3, 13, 30, tzinfo=timezone.utc),
                is_realtime=False,
                is_delayed=True,
                delay_minutes=15,
                bids=[ProviderOrderBookLevel(price=Decimal("101.20"), volume=Decimal("1000"), amount=Decimal("101200"), order_count=5)],
                asks=[ProviderOrderBookLevel(price=Decimal("101.30"), volume=Decimal("800"), amount=Decimal("81040"), order_count=4)],
                recent_trades=[
                    ProviderRecentTrade(
                        timestamp=datetime(2026, 7, 3, 13, 31, tzinfo=timezone.utc),
                        price=Decimal("101.25"),
                        volume=Decimal("15000"),
                        amount=Decimal("1518750"),
                        side="buy",
                    )
                ],
                fund_flow=ProviderFundFlow(
                    currency="CNY",
                    net_inflow=Decimal("1234567"),
                    source_definition="provider-defined verified fund-flow",
                ),
            )

    monkeypatch.setattr(market_data_service, "get_provider", lambda provider_name=None: FakeDepthProvider())
    client = TestClient(app)

    response = client.get(
        "/market-data/AAPL/depth",
        params={"provider": "akshare", "depth_levels": 5, "large_order_threshold_amount": "1000000"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["source"] == "provider"
    assert payload["provider"] == "fake_depth"
    assert payload["effective_provider"] == "akshare"
    assert payload["order_book"]["status"] == "ok"
    assert payload["recent_trades"]["status"] == "ok"
    assert payload["large_orders"]["status"] == "ok"
    assert payload["fund_flow"]["status"] == "ok"
    assert payload["large_orders"]["items"][0]["threshold_amount"] == 1000000.0


def test_get_market_depth_returns_degraded_contract_for_unsupported_provider():
    client = TestClient(app)

    response = client.get("/market-data/AAPL/depth", params={"provider": "yfinance"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "AAPL"
    assert payload["source"] == "none"
    assert payload["provider"] == "yfinance"
    assert payload["requested_provider"] == "yfinance"
    assert payload["effective_provider"] == "yfinance"
    assert payload["status"] == "degraded"
    assert payload["as_of"] is None
    assert payload["is_realtime"] is False
    assert payload["is_delayed"] is False
    assert payload["delay_minutes"] is None
    assert payload["order_book"] == {
        "status": "degraded",
        "reason": market_data_service.MARKET_DEPTH_PROVIDER_CAPABILITIES["yfinance"]["reason"],
        "as_of": None,
        "depth_levels": market_data_service.DEFAULT_MARKET_DEPTH_LEVELS,
        "bids": [],
        "asks": [],
    }
    assert payload["recent_trades"] == {
        "status": "degraded",
        "reason": market_data_service.RECENT_TRADES_UNSUPPORTED_REASON,
        "as_of": None,
        "items": [],
    }
    assert payload["large_orders"] == {
        "status": "degraded",
        "reason": market_data_service.LARGE_ORDERS_UNSUPPORTED_REASON,
        "threshold_amount": 1000000.0,
        "threshold_volume": None,
        "currency": None,
        "as_of": None,
        "items": [],
    }
    assert payload["fund_flow"] == {
        "status": "degraded",
        "reason": market_data_service.FUND_FLOW_UNSUPPORTED_REASON,
        "as_of": None,
        "currency": None,
        "net_inflow": None,
        "main_net_inflow": None,
        "retail_net_inflow": None,
        "source_definition": None,
    }
    assert payload["availability"] == {
        "status": "degraded",
        "reason": market_data_service.MARKET_DEPTH_UNSUPPORTED_REASON,
        "capabilities": {
            "order_book": False,
            "recent_trades": False,
            "large_orders": False,
            "fund_flow": False,
        },
    }


def test_get_market_depth_uses_platform_default_provider_when_omitted(monkeypatch):
    monkeypatch.setattr(
        market_data_service,
        "get_effective_market_data_provider",
        lambda requested=None: "mock" if requested is None else str(requested).strip().lower(),
    )
    client = TestClient(app)

    response = client.get("/market-data/AAPL/depth")

    assert response.status_code == 200
    payload = response.json()
    assert payload["requested_provider"] is None
    assert payload["effective_provider"] == "mock"
    assert payload["order_book"]["reason"] == market_data_service.MARKET_DEPTH_PROVIDER_CAPABILITIES["mock"]["reason"]


def test_get_market_depth_applies_depth_levels_and_large_order_threshold():
    client = TestClient(app)

    response = client.get(
        "/market-data/AAPL/depth",
        params={
            "provider": "mock",
            "depth_levels": 3,
            "large_order_threshold_amount": "2500000.50",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["order_book"]["depth_levels"] == 3
    assert payload["large_orders"]["threshold_amount"] == 2500000.5


def test_get_market_depth_rejects_invalid_depth_levels():
    client = TestClient(app)

    response = client.get(
        "/market-data/AAPL/depth",
        params={"provider": "mock", "depth_levels": 0},
    )

    assert response.status_code == 422


def test_get_market_depth_rejects_invalid_large_order_threshold():
    client = TestClient(app)

    response = client.get(
        "/market-data/AAPL/depth",
        params={"provider": "mock", "large_order_threshold_amount": "0"},
    )

    assert response.status_code == 422


def test_get_market_depth_rejects_unknown_provider():
    client = TestClient(app)

    response = client.get("/market-data/AAPL/depth", params={"provider": "unknown"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported market data provider: unknown"
