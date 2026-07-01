from collections.abc import Callable
from datetime import date
from decimal import Decimal

import pandas as pd

from packages.providers.base import ProviderBar, ProviderInstrument
from packages.providers.yfinance_helpers import map_symbol_to_ticker


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

        ticker = map_symbol_to_ticker(symbol)
        frame = _normalize_downloaded_frame(self._downloader(ticker, start, end), ticker)
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


def _decimal(value: object) -> Decimal:
    return Decimal(str(value))


def _normalize_downloaded_frame(frame: pd.DataFrame, ticker: str) -> pd.DataFrame:
    if not isinstance(frame.columns, pd.MultiIndex):
        return frame

    price_level_index = _find_price_level_index(frame.columns)
    if price_level_index is None:
        return frame

    ticker_level_indices = [
        level_index
        for level_index in range(frame.columns.nlevels)
        if level_index != price_level_index
    ]
    if len(ticker_level_indices) == 1:
        ticker_level_index = ticker_level_indices[0]
        try:
            return frame.xs(ticker, axis=1, level=ticker_level_index, drop_level=True)
        except KeyError:
            pass

    normalized_frame = frame.copy()
    normalized_frame.columns = frame.columns.get_level_values(price_level_index)
    return normalized_frame


def _find_price_level_index(columns: pd.MultiIndex) -> int | None:
    required_price_columns = {"Open", "High", "Low", "Close", "Volume"}
    for level_index in range(columns.nlevels):
        level_values = {str(value) for value in columns.get_level_values(level_index)}
        if required_price_columns.issubset(level_values):
            return level_index
    return None
