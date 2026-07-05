from datetime import date, datetime, timezone
from decimal import Decimal

import pandas as pd

from packages.providers.akshare_provider import AkShareProvider
from packages.providers.tushare_provider import TushareProvider
from packages.services.market_data import get_provider


def _sample_cn_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2026-01-02", "2026-01-03"]),
            "open": [1800.0, 1810.0],
            "high": [1820.0, 1830.0],
            "low": [1790.0, 1805.0],
            "close": [1815.0, 1825.0],
            "volume": [100000.0, 120000.0],
            "amount": [1_000_000_000.0, 1_200_000_000.0],
        }
    )


def test_akshare_provider_fetch_bars_with_mock_downloader():
    provider = AkShareProvider(downloader=lambda _symbol, _start, _end: _sample_cn_frame())
    bars = provider.fetch_bars("600519", "1d", date(2026, 1, 1), date(2026, 1, 10))

    assert len(bars) == 2
    assert bars[0].symbol == "600519"
    assert float(bars[0].close) == 1815.0


def test_akshare_provider_fetches_market_depth_from_injected_payload():
    def fake_market_depth_downloader(symbol: str, depth_levels: int) -> dict[str, object]:
        assert symbol == "600519"
        assert depth_levels == 5
        return {
            "source": "akshare.fixture",
            "as_of": "2026-07-03T13:30:00+00:00",
            "is_realtime": False,
            "is_delayed": True,
            "delay_minutes": 15,
            "bids": pd.DataFrame(
                [
                    {"price": "101.20", "volume": "1000", "amount": "101200", "order_count": "5"},
                    {"price": "101.10", "volume": "800", "amount": "80880", "order_count": "4"},
                ]
            ),
            "asks": pd.DataFrame(
                [
                    {"price": "101.30", "volume": "900", "amount": "91170", "order_count": "3"},
                ]
            ),
            "recent_trades": pd.DataFrame(
                [
                    {
                        "timestamp": "2026-07-03T13:31:00+00:00",
                        "price": "101.25",
                        "volume": "15000",
                        "amount": "1518750",
                        "side": "buy",
                    }
                ]
            ),
            "fund_flow": {
                "currency": "CNY",
                "net_inflow": "1234567",
                "main_net_inflow": "765432",
                "retail_net_inflow": "-12345",
                "source_definition": "AkShare fixture fund-flow",
            },
        }

    provider = AkShareProvider(
        downloader=lambda _symbol, _start, _end: (_ for _ in ()).throw(AssertionError("daily bars must not be used")),
        market_depth_downloader=fake_market_depth_downloader,
    )

    snapshot = provider.fetch_market_depth("600519", 5)

    assert snapshot.provider == "akshare"
    assert snapshot.source == "akshare.fixture"
    assert snapshot.as_of == datetime(2026, 7, 3, 13, 30, tzinfo=timezone.utc)
    assert snapshot.is_delayed is True
    assert snapshot.delay_minutes == 15
    assert snapshot.bids[0].price == Decimal("101.20")
    assert snapshot.bids[0].volume == Decimal("1000")
    assert snapshot.bids[0].order_count == 5
    assert snapshot.asks[0].price == Decimal("101.30")
    assert snapshot.recent_trades[0].amount == Decimal("1518750")
    assert snapshot.recent_trades[0].side == "buy"
    assert snapshot.fund_flow is not None
    assert snapshot.fund_flow.net_inflow == Decimal("1234567")
    assert snapshot.availability["status"] == "ok"


def test_akshare_provider_returns_degraded_market_depth_for_empty_payload():
    provider = AkShareProvider(market_depth_downloader=lambda _symbol, _depth_levels: {})

    snapshot = provider.fetch_market_depth("600519", 5)

    assert snapshot.bids == []
    assert snapshot.asks == []
    assert snapshot.recent_trades == []
    assert snapshot.fund_flow is None
    assert snapshot.availability["status"] == "degraded"


def test_tushare_provider_fetch_bars_with_mock_downloader():
    provider = TushareProvider(downloader=lambda _symbol, _start, _end: _sample_cn_frame())
    bars = provider.fetch_bars("600519", "1d", date(2026, 1, 1), date(2026, 1, 10))

    assert len(bars) == 2
    assert bars[0].symbol == "600519"


def test_get_provider_resolves_akshare_and_tushare():
    assert type(get_provider("akshare")).__name__ == "AkShareProvider"
    assert type(get_provider("tushare")).__name__ == "TushareProvider"
