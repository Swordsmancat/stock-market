from datetime import date
from decimal import Decimal

import pandas as pd

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


def test_yfinance_provider_maps_known_market_instruments():
    provider = YFinanceProvider(downloader=lambda ticker, start, end: pd.DataFrame())

    instruments = provider.fetch_instruments("HK")

    assert instruments[0].symbol == "0700"
    assert instruments[0].market == "HK"
    assert instruments[0].currency == "HKD"
