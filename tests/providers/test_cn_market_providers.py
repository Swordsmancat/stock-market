from datetime import date, datetime, timezone
from decimal import Decimal
import sys
from types import SimpleNamespace

import pandas as pd
import pytest

from packages.providers.akshare_provider import AkShareProvider
from packages.providers.cn_market_helpers import tushare_ts_code
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


def _install_tushare_daily(monkeypatch, daily):
    monkeypatch.setitem(
        sys.modules,
        "packages.services.platform_settings",
        SimpleNamespace(get_platform_settings=lambda: {"tushare_token": "test-token"}),
    )
    monkeypatch.setitem(
        sys.modules,
        "tushare",
        SimpleNamespace(
            set_token=lambda _token: None,
            pro_api=lambda *_args: SimpleNamespace(daily=daily),
        ),
    )


def test_akshare_provider_fetch_bars_with_mock_downloader():
    provider = AkShareProvider(downloader=lambda _symbol, _start, _end: _sample_cn_frame())
    bars = provider.fetch_bars("600519", "1d", date(2026, 1, 1), date(2026, 1, 10))

    assert len(bars) == 2
    assert bars[0].symbol == "600519"
    assert float(bars[0].close) == 1815.0


def test_akshare_provider_does_not_convert_provider_failure_into_no_data():
    def fail_download(_symbol, _start, _end):
        raise TimeoutError("upstream timeout")

    provider = AkShareProvider(downloader=fail_download)

    with pytest.raises(TimeoutError, match="upstream timeout"):
        provider.fetch_bars("600519", "1d", date(2026, 1, 1), date(2026, 1, 10))


def test_akshare_provider_normalizes_exact_trade_date_intraday_bars():
    frame = pd.DataFrame(
        {
            "timestamp": ["2026-07-14 15:00:00", "2026-07-15 09:31:00"],
            "open": [100, 101],
            "high": [102, 103],
            "low": [99, 100],
            "close": [101, 102],
            "volume": [1000, 1200],
            "amount": [101000, 122400],
            "average_price": [100.5, 101.5],
        }
    )
    provider = AkShareProvider(
        intraday_downloader=lambda _symbol, _trade_date, _timeframe: frame
    )

    bars = provider.fetch_intraday_bars("600519", date(2026, 7, 15), "1m")

    assert len(bars) == 1
    assert bars[0].symbol == "600519"
    assert bars[0].timestamp.isoformat() == "2026-07-15T09:31:00+08:00"
    assert bars[0].close == Decimal("102")
    assert bars[0].volume == 1200
    assert bars[0].amount == Decimal("122400")
    assert bars[0].average_price == Decimal("101.5")


def test_akshare_provider_keeps_empty_intraday_frame_as_no_data():
    provider = AkShareProvider(
        intraday_downloader=lambda _symbol, _trade_date, _timeframe: pd.DataFrame()
    )

    bars = provider.fetch_intraday_bars("600519", date(2026, 7, 15), "1m")

    assert bars == []


def test_akshare_provider_rejects_malformed_intraday_schema():
    frame = pd.DataFrame(
        {
            "timestamp": ["2026-07-15 09:31:00"],
            "open": [101],
            "high": [103],
            "low": [100],
            "volume": [1200],
        }
    )
    provider = AkShareProvider(
        intraday_downloader=lambda _symbol, _trade_date, _timeframe: frame
    )

    with pytest.raises(TypeError, match="intraday close is malformed"):
        provider.fetch_intraday_bars("600519", date(2026, 7, 15), "1m")


def test_akshare_eastmoney_intraday_downloader_normalizes_public_frame(monkeypatch):
    captured: dict[str, object] = {}

    def stock_zh_a_hist_min_em(**kwargs):
        captured.update(kwargs)
        return pd.DataFrame(
            {
                "时间": ["2026-07-15 09:31:00"],
                "开盘": [101],
                "收盘": [102],
                "最高": [103],
                "最低": [100],
                "成交量": [1200],
                "成交额": [122400],
                "均价": [101.5],
            }
        )

    monkeypatch.setitem(
        sys.modules,
        "akshare",
        SimpleNamespace(stock_zh_a_hist_min_em=stock_zh_a_hist_min_em),
    )

    bars = AkShareProvider().fetch_intraday_bars(
        "600519",
        date(2026, 7, 15),
        "1m",
    )

    assert captured == {
        "symbol": "600519",
        "start_date": "2026-07-15 00:00:00",
        "end_date": "2026-07-15 23:59:59",
        "period": "1",
        "adjust": "",
    }
    assert len(bars) == 1
    assert bars[0].timestamp.isoformat() == "2026-07-15T09:31:00+08:00"
    assert bars[0].average_price == Decimal("101.5")


@pytest.mark.parametrize(
    ("symbol", "expected_provider_symbol"),
    [("600519", "sh600519"), ("000001", "sz000001"), ("920002", "bj920002")],
)
def test_akshare_sina_intraday_downloader_maps_cn_exchange_prefix(
    monkeypatch,
    symbol,
    expected_provider_symbol,
):
    captured: dict[str, object] = {}

    def stock_zh_a_minute(**kwargs):
        captured.update(kwargs)
        return pd.DataFrame(
            {
                "day": ["2026-07-15 09:31:00"],
                "open": [101],
                "high": [103],
                "low": [100],
                "close": [102],
                "volume": [1200],
                "amount": [122400],
            }
        )

    monkeypatch.setitem(
        sys.modules,
        "akshare",
        SimpleNamespace(stock_zh_a_minute=stock_zh_a_minute),
    )
    provider = AkShareProvider(
        intraday_downloader=AkShareProvider.download_sina_intraday_bars
    )

    bars = provider.fetch_intraday_bars(symbol, date(2026, 7, 15), "1m")

    assert captured == {
        "symbol": expected_provider_symbol,
        "period": "1",
        "adjust": "",
    }
    assert len(bars) == 1
    assert bars[0].symbol == symbol
    assert bars[0].timestamp.isoformat() == "2026-07-15T09:31:00+08:00"


def test_akshare_sina_daily_downloader_prefixes_symbol_and_normalizes_frame(monkeypatch):
    captured: dict[str, object] = {}

    def stock_zh_a_daily(**kwargs):
        captured.update(kwargs)
        return pd.DataFrame(
            {
                "date": ["2026-07-09"],
                "open": [100],
                "high": [102],
                "low": [99],
                "close": [101],
                "volume": [1000],
                "amount": [101000],
            }
        )

    monkeypatch.setitem(sys.modules, "akshare", SimpleNamespace(stock_zh_a_daily=stock_zh_a_daily))

    frame = AkShareProvider.download_sina_daily_bars(
        "600519", date(2026, 7, 1), date(2026, 7, 10)
    )

    assert captured == {
        "symbol": "sh600519",
        "start_date": "20260701",
        "end_date": "20260710",
        "adjust": "qfq",
    }
    assert frame.to_dict("records") == [
        {
            "timestamp": pd.Timestamp("2026-07-09"),
            "open": 100,
            "high": 102,
            "low": 99,
            "close": 101,
            "volume": 1000,
            "amount": 101000,
        }
    ]


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
        downloader=lambda _symbol, _start, _end: (_ for _ in ()).throw(
            AssertionError("daily bars must not be used")
        ),
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


@pytest.mark.parametrize(
    ("symbol", "expected_ts_code"),
    [
        ("600519", "600519.SH"),
        ("000001", "000001.SZ"),
        ("300750", "300750.SZ"),
        ("430047", "430047.BJ"),
        ("830799", "830799.BJ"),
        ("920000", "920000.BJ"),
    ],
)
def test_tushare_downloader_uses_exact_exchange_ts_code(
    monkeypatch,
    symbol: str,
    expected_ts_code: str,
):
    calls: list[dict[str, object]] = []

    def daily(**kwargs):
        calls.append(kwargs)
        return pd.DataFrame(
            [
                {
                    "trade_date": "20260709",
                    "open": 100,
                    "high": 102,
                    "low": 99,
                    "close": 101,
                    "vol": 1000,
                    "amount": 101000,
                }
            ]
        )

    _install_tushare_daily(monkeypatch, daily)

    frame = TushareProvider._download(symbol, date(2026, 7, 1), date(2026, 7, 10))

    assert tushare_ts_code(symbol) == expected_ts_code
    assert [call["ts_code"] for call in calls] == [expected_ts_code]
    assert frame["timestamp"].tolist() == [pd.Timestamp("2026-07-09")]


def test_tushare_downloader_reports_missing_dependency_as_unavailable(monkeypatch):
    monkeypatch.setitem(sys.modules, "tushare", None)

    with pytest.raises(RuntimeError, match="tushare package is not installed"):
        TushareProvider._download("600519", date(2026, 7, 1), date(2026, 7, 10))


def test_tushare_downloader_does_not_convert_provider_failure_into_no_data(monkeypatch):
    def daily(**_kwargs):
        raise RuntimeError("provider rate limited")

    _install_tushare_daily(monkeypatch, daily)

    with pytest.raises(RuntimeError, match="provider rate limited"):
        TushareProvider._download("600519", date(2026, 7, 1), date(2026, 7, 10))


def test_tushare_downloader_does_not_convert_schema_failure_into_no_data(monkeypatch):
    def daily(**_kwargs):
        return pd.DataFrame([{"trade_date": "20260709", "open": 100}])

    _install_tushare_daily(monkeypatch, daily)

    with pytest.raises(KeyError):
        TushareProvider._download("600519", date(2026, 7, 1), date(2026, 7, 10))


def test_tushare_downloader_keeps_empty_provider_result_as_no_data(monkeypatch):
    _install_tushare_daily(monkeypatch, lambda **_kwargs: pd.DataFrame())

    frame = TushareProvider._download("600519", date(2026, 7, 1), date(2026, 7, 10))

    assert frame.empty


def test_get_provider_resolves_akshare_and_tushare():
    assert type(get_provider("akshare")).__name__ == "AkShareProvider"
    assert type(get_provider("tushare")).__name__ == "TushareProvider"
