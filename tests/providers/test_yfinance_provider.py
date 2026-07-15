from datetime import date, datetime, timezone
from decimal import Decimal

import pandas as pd
import pytest

from packages.providers.yfinance_provider import YFinanceProvider


def test_yfinance_provider_returns_provider_bars_from_downloaded_dataframe():
    def fake_download(ticker: str, start: date, end: date) -> pd.DataFrame:
        assert ticker == "AAPL"
        assert start == date(2026, 1, 1)
        assert end == date(2026, 1, 3)
        return pd.DataFrame(
            [
                {
                    "Open": 100.0,
                    "High": 103.0,
                    "Low": 99.0,
                    "Close": 102.0,
                    "Volume": 1000,
                }
            ],
            index=pd.to_datetime(["2026-01-01"]),
        )

    provider = YFinanceProvider(downloader=fake_download)

    bars = provider.fetch_bars("AAPL", "1d", date(2026, 1, 1), date(2026, 1, 3))

    assert len(bars) == 1
    assert bars[0].symbol == "AAPL"
    assert bars[0].timestamp == date(2026, 1, 1)
    assert bars[0].open == Decimal("100.0")
    assert bars[0].close == Decimal("102.0")
    assert bars[0].volume == Decimal("1000")


def test_yfinance_provider_accepts_multi_index_downloaded_dataframe():
    def fake_download(ticker: str, start: date, end: date) -> pd.DataFrame:
        assert ticker == "AAPL"
        columns = pd.MultiIndex.from_tuples(
            [
                ("Close", "AAPL"),
                ("High", "AAPL"),
                ("Low", "AAPL"),
                ("Open", "AAPL"),
                ("Volume", "AAPL"),
            ],
            names=["Price", "Ticker"],
        )
        return pd.DataFrame(
            [[102.0, 103.0, 99.0, 100.0, 1000]],
            columns=columns,
            index=pd.to_datetime(["2026-01-01"]),
        )

    provider = YFinanceProvider(downloader=fake_download)

    bars = provider.fetch_bars("AAPL", "1d", date(2026, 1, 1), date(2026, 1, 3))

    assert len(bars) == 1
    assert bars[0].symbol == "AAPL"
    assert bars[0].timestamp == date(2026, 1, 1)
    assert bars[0].open == Decimal("100.0")
    assert bars[0].high == Decimal("103.0")
    assert bars[0].low == Decimal("99.0")
    assert bars[0].close == Decimal("102.0")
    assert bars[0].volume == Decimal("1000")


def test_yfinance_provider_maps_known_market_instruments():
    provider = YFinanceProvider(downloader=lambda ticker, start, end: pd.DataFrame())

    instruments = provider.fetch_instruments("HK")

    assert instruments[0].symbol == "0700"
    assert instruments[0].market == "HK"
    assert instruments[0].currency == "HKD"


@pytest.mark.parametrize(
    ("market", "symbol", "expected_ticker"),
    [
        ("CN", "000001", "000001.SZ"),
        ("CN", "600000", "600000.SS"),
        ("CN", "920000", "920000.BJ"),
        ("HK", "9988", "9988.HK"),
        ("US", "AAPL", "AAPL"),
        ("CN", "000001.SS", "000001.SS"),
    ],
)
def test_yfinance_provider_maps_canonical_symbols_with_explicit_market(
    market: str,
    symbol: str,
    expected_ticker: str,
):
    requested_tickers: list[str] = []

    def fake_download(ticker: str, start: date, end: date) -> pd.DataFrame:
        requested_tickers.append(ticker)
        return pd.DataFrame()

    provider = YFinanceProvider(downloader=fake_download, market=market)

    assert provider.fetch_bars(symbol, "1d", date(2026, 7, 1), date(2026, 7, 2)) == []
    assert requested_tickers == [expected_ticker]


def test_yfinance_provider_fetches_intraday_bars_with_one_minute_interval():
    def fake_download(ticker: str, start: date, end: date, interval: str | None = None) -> pd.DataFrame:
        assert ticker == "AAPL"
        assert start == date(2026, 7, 3)
        assert end == date(2026, 7, 4)
        assert interval == "1m"
        return pd.DataFrame(
            [
                {
                    "Open": 214.1,
                    "High": 214.3,
                    "Low": 213.9,
                    "Close": 214.2,
                    "Volume": 12000,
                },
                {
                    "Open": 215.1,
                    "High": 215.3,
                    "Low": 214.9,
                    "Close": 215.2,
                    "Volume": 9000,
                },
            ],
            index=pd.to_datetime(["2026-07-03T13:30:00+00:00", "2026-07-04T13:30:00+00:00"]),
        )

    provider = YFinanceProvider(downloader=fake_download)

    bars = provider.fetch_intraday_bars("AAPL", date(2026, 7, 3), "1m")

    assert len(bars) == 1
    assert bars[0].symbol == "AAPL"
    assert bars[0].timestamp == datetime(2026, 7, 3, 13, 30, tzinfo=timezone.utc)
    assert bars[0].open == Decimal("214.1")
    assert bars[0].close == Decimal("214.2")
    assert bars[0].volume == 12000
    assert bars[0].amount is None
    assert bars[0].average_price is None


def test_yfinance_provider_returns_empty_intraday_bars_for_empty_frame():
    provider = YFinanceProvider(downloader=lambda ticker, start, end, interval=None: pd.DataFrame())

    bars = provider.fetch_intraday_bars("AAPL", date(2026, 7, 3), "1m")

    assert bars == []


def test_yfinance_provider_does_not_fabricate_intraday_rows_from_missing_columns():
    def fake_download(ticker: str, start: date, end: date, interval: str | None = None) -> pd.DataFrame:
        return pd.DataFrame(
            [{"Open": 214.1, "High": 214.3, "Low": 213.9, "Close": 214.2}],
            index=pd.to_datetime(["2026-07-03T13:30:00+00:00"]),
        )

    provider = YFinanceProvider(downloader=fake_download)

    bars = provider.fetch_intraday_bars("AAPL", date(2026, 7, 3), "1m")

    assert bars == []


def test_yfinance_provider_rejects_unsupported_intraday_timeframes():
    provider = YFinanceProvider(downloader=lambda ticker, start, end, interval=None: pd.DataFrame())

    with pytest.raises(ValueError, match="Unsupported intraday timeframe"):
        provider.fetch_intraday_bars("AAPL", date(2026, 7, 3), "5m")
