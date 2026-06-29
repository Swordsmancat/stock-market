from collections.abc import Callable
from datetime import date
from decimal import Decimal

import pandas as pd

from packages.providers.base import ProviderBar, ProviderInstrument


Downloader = Callable[[str, date, date], pd.DataFrame]


class YFinanceProvider:
    def __init__(self, downloader: Downloader | None = None) -> None:
        self._downloader = downloader or self._download

    def fetch_instruments(
        self,
        market: str,
        exchange: str | None = None,
    ) -> list[ProviderInstrument]:
        fixtures = {
            "CN": [ProviderInstrument("600519", "Kweichow Moutai", "CN", "SSE", "stock", "CNY")],
            "HK": [ProviderInstrument("0700", "Tencent Holdings", "HK", "HKEX", "stock", "HKD")],
            "US": [ProviderInstrument("AAPL", "Apple Inc.", "US", "NASDAQ", "stock", "USD")],
        }
        instruments = fixtures.get(market, [])
        if exchange is None:
            return instruments
        return [instrument for instrument in instruments if instrument.exchange == exchange]

    def fetch_bars(self, symbol: str, timeframe: str, start: date, end: date) -> list[ProviderBar]:
        if timeframe != "1d":
            msg = f"Unsupported timeframe for yfinance provider: {timeframe}"
            raise ValueError(msg)

        ticker = _map_symbol_to_ticker(symbol)
        frame = self._downloader(ticker, start, end)
        bars: list[ProviderBar] = []

        for timestamp, row in frame.iterrows():
            trade_date = timestamp.date() if hasattr(timestamp, "date") else timestamp
            bars.append(
                ProviderBar(
                    symbol=symbol,
                    timestamp=trade_date,
                    open=_decimal(row["Open"]),
                    high=_decimal(row["High"]),
                    low=_decimal(row["Low"]),
                    close=_decimal(row["Close"]),
                    volume=_decimal(row["Volume"]),
                    amount=None,
                )
            )
        return bars

    def _download(self, ticker: str, start: date, end: date) -> pd.DataFrame:
        import yfinance as yf

        return yf.download(ticker, start=start.isoformat(), end=end.isoformat(), progress=False)


def _map_symbol_to_ticker(symbol: str) -> str:
    if symbol == "0700":
        return "0700.HK"
    if symbol == "600519":
        return "600519.SS"
    return symbol


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))
