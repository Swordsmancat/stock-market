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


def test_akshare_provider_normalizes_complete_a_share_universe():
    frame = pd.DataFrame(
        [
            {"code": "600519", "name": "Kweichow Moutai"},
            {"code": "000001", "name": "Ping An Bank"},
            {"code": "430047", "name": "Novogene"},
            {"code": "600519", "name": "Kweichow Moutai"},
        ]
    )
    provider = AkShareProvider(instrument_universe_downloader=lambda: frame)

    snapshot = provider.fetch_instrument_universe("cn")

    assert snapshot.status == "ok"
    assert snapshot.is_complete is True
    assert [(item.symbol, item.exchange) for item in snapshot.items] == [
        ("000001", "SZSE"),
        ("430047", "BSE"),
        ("600519", "SSE"),
    ]
    assert snapshot.availability["row_count"] == 3
    assert snapshot.diagnostics == [
        {
            "code": "INSTRUMENT_UNIVERSE_DUPLICATES_DEDUPED",
            "message": "Duplicate provider symbols were deterministically de-duplicated.",
            "details": {"duplicate_count": 1},
        }
    ]


def test_akshare_provider_marks_universe_incomplete_when_rows_are_skipped():
    frame = pd.DataFrame(
        [
            {"证券代码": "920001", "证券简称": "Beijing Sample"},
            {"证券代码": "not-a-symbol", "证券简称": "Invalid"},
        ]
    )
    provider = AkShareProvider(instrument_universe_downloader=lambda: frame)

    snapshot = provider.fetch_instrument_universe("CN")

    assert snapshot.status == "degraded"
    assert snapshot.is_complete is False
    assert [(item.symbol, item.exchange) for item in snapshot.items] == [("920001", "BSE")]
    assert snapshot.diagnostics[0]["details"] == {"skipped_count": 1}


def test_akshare_provider_returns_unavailable_for_empty_universe():
    provider = AkShareProvider(instrument_universe_downloader=pd.DataFrame)

    snapshot = provider.fetch_instrument_universe("CN")

    assert snapshot.status == "unavailable"
    assert snapshot.items == []
    assert snapshot.is_complete is False
    assert snapshot.diagnostics[0]["code"] == "INSTRUMENT_UNIVERSE_EMPTY"


def test_akshare_provider_rejects_unsupported_universe_market_without_download():
    def fail_if_called() -> pd.DataFrame:
        raise AssertionError("unsupported markets must not call AkShare")

    provider = AkShareProvider(instrument_universe_downloader=fail_if_called)

    snapshot = provider.fetch_instrument_universe("US")

    assert snapshot.status == "unavailable"
    assert snapshot.items == []
    assert snapshot.diagnostics[0]["code"] == "INSTRUMENT_UNIVERSE_MARKET_UNSUPPORTED"


def test_akshare_provider_normalizes_dividend_bonus_actions_for_requested_symbols():
    frame = pd.DataFrame(
        [
            {
                "代码": "600519",
                "名称": "Kweichow Moutai",
                "预案公告日": "2026-03-20",
                "股权登记日": "2026-06-25",
                "除权除息日": "2026-06-26",
                "现金分红-现金分红比例": "276.65",
                "送转股份-送股比例": "0",
                "送转股份-转股比例": "0",
                "方案进度": "implemented",
            },
            {"代码": "000001", "名称": "Ping An Bank", "预案公告日": "2026-03-21"},
        ]
    )
    provider = AkShareProvider(dividend_bonus_downloader=lambda _period: frame)

    snapshot = provider.fetch_corporate_actions(
        "dividend_bonus",
        date(2025, 12, 31),
        ["600519"],
    )

    assert snapshot.status == "ok"
    assert len(snapshot.items) == 1
    item = snapshot.items[0]
    assert item["symbol"] == "600519"
    assert item["trade_date"] == "2026-06-26"
    assert item["cash_dividend_per_10"] == 276.65
    assert item["action_status"] == "implemented"


def test_akshare_provider_keeps_partial_rights_allotment_results():
    def rights_downloader(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        assert start_date == "20250101"
        assert end_date == "20251231"
        if symbol == "000002":
            raise RuntimeError("provider unavailable")
        return pd.DataFrame(
            [
                {
                    "证券代码": symbol,
                    "证券简称": "Sample",
                    "公告日期": "2025-05-01",
                    "配股缴款起始日": "2025-05-10",
                    "配股缴款截止日": "2025-05-20",
                    "配股代码": "080001",
                    "配股比例": "0.3",
                    "配股价格": "8.5",
                }
            ]
        )

    provider = AkShareProvider(rights_allotment_downloader=rights_downloader)

    snapshot = provider.fetch_corporate_actions(
        "rights_allotment",
        date(2025, 12, 31),
        ["000001", "000002"],
    )

    assert snapshot.status == "degraded"
    assert len(snapshot.items) == 1
    assert snapshot.items[0]["symbol"] == "000001"
    assert snapshot.items[0]["rights_ratio"] == 0.3
    assert snapshot.items[0]["rights_price"] == 8.5
    assert snapshot.diagnostics[0]["details"] == {
        "symbol": "000002",
        "exception_type": "RuntimeError",
    }


def test_tushare_provider_fetch_bars_with_mock_downloader():
    provider = TushareProvider(downloader=lambda _symbol, _start, _end: _sample_cn_frame())
    bars = provider.fetch_bars("600519", "1d", date(2026, 1, 1), date(2026, 1, 10))

    assert len(bars) == 2
    assert bars[0].symbol == "600519"


def test_get_provider_resolves_akshare_and_tushare():
    assert type(get_provider("akshare")).__name__ == "AkShareProvider"
    assert type(get_provider("tushare")).__name__ == "TushareProvider"
