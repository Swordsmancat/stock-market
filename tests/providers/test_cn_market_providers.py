from datetime import date
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


def test_tushare_provider_fetch_bars_with_mock_downloader():
    provider = TushareProvider(downloader=lambda _symbol, _start, _end: _sample_cn_frame())
    bars = provider.fetch_bars("600519", "1d", date(2026, 1, 1), date(2026, 1, 10))

    assert len(bars) == 2
    assert bars[0].symbol == "600519"


def test_get_provider_resolves_akshare_and_tushare():
    assert type(get_provider("akshare")).__name__ == "AkShareProvider"
    assert type(get_provider("tushare")).__name__ == "TushareProvider"
