from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import packages.domain.models  # noqa: F401
from packages.services.market_dashboard import get_market_overview_payload
from packages.services.market_data import MarketDataProviderUnavailableError
from packages.shared.cache import clear_market_overview_cache
from packages.shared.database import Base


def make_session():
    clear_market_overview_cache("mock")
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_market_overview_payload_contains_followed_indices_and_valuation_sections():
    session = make_session()

    payload = get_market_overview_payload(
        session=session,
        provider_name="mock",
        today=date(2026, 7, 3),
    )

    assert payload["provider"] == "mock"
    assert payload["range"] == {
        "timeframe": "1d",
        "start": "2026-04-02",
        "end": "2026-07-03",
    }

    followed_items = payload["followed"]["items"]
    assert payload["followed"]["scope"] == "watchlist"
    assert len(followed_items) == 1
    assert followed_items[0]["symbol"] == "AAPL"
    assert followed_items[0]["detail_path"] == "/instruments/AAPL"
    assert followed_items[0]["status"] == "ok"
    assert followed_items[0]["latest"]["movement"]["direction"] == "up"

    index_items = payload["indices"]["items"]
    assert len(index_items) == 10
    assert index_items[0]["code"] == "cn_shanghai_composite"
    assert index_items[0]["provider_symbol"] == "SH000001"
    assert index_items[-1]["code"] == "us_dow_jones"

    valuation_items = payload["valuation_indicators"]["items"]
    assert [item["region"] for item in valuation_items] == ["CN", "HK", "US"]
    assert all(item["status"] == "no_data" for item in valuation_items)


def test_market_overview_keeps_partial_results_when_index_provider_fails(monkeypatch):
    session = make_session()

    def fake_get_bars_payload(symbol, timeframe, start, end, session=None, provider_name=None):
        if symbol == "SPX":
            raise MarketDataProviderUnavailableError("mock", "fetching bars", ConnectionError("down"))
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "source": "mock",
            "provider": "mock",
            "requested_provider": "mock",
            "effective_provider": "mock",
            "status": "ok",
            "no_data_reason": None,
            "items": [
                {"timestamp": "2026-07-02", "open": 100, "high": 103, "low": 99, "close": 101, "volume": 1000},
                {"timestamp": "2026-07-03", "open": 101, "high": 104, "low": 100, "close": 102, "volume": 1100},
            ],
        }

    monkeypatch.setattr(
        "packages.services.market_dashboard.get_bars_payload",
        fake_get_bars_payload,
    )

    payload = get_market_overview_payload(
        session=session,
        provider_name="mock",
        today=date(2026, 7, 3),
    )

    unavailable_indices = [item for item in payload["indices"]["items"] if item["status"] == "unavailable"]
    assert len(unavailable_indices) == 1
    assert unavailable_indices[0]["code"] == "us_sp_500"
    assert payload["followed"]["items"][0]["status"] == "ok"
    assert payload["diagnostics"][0]["section"] == "indices"
    assert payload["diagnostics"][0]["code"] == "us_sp_500"
