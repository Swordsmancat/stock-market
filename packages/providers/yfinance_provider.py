from collections.abc import Callable
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation

import pandas as pd

from packages.providers.base import ProviderBar, ProviderInstrument, ProviderIntradayBar
from packages.providers.yfinance_helpers import map_symbol_to_ticker


Downloader = Callable[..., pd.DataFrame]


class YFinanceProvider:
    def __init__(self, downloader: Downloader | None = None, market: str | None = None) -> None:
        self._downloader = downloader or self._download
        self._market = market.strip().upper() if market and market.strip() else None

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

        ticker = map_symbol_to_ticker(symbol, self._market)
        frame = _normalize_downloaded_frame(self._downloader(ticker, start, end), ticker)
        bars: list[ProviderBar] = []

        for timestamp, row in frame.iterrows():
            trade_date = timestamp.date() if hasattr(timestamp, "date") else timestamp
            open_value = _decimal_or_none(row["Open"])
            high_value = _decimal_or_none(row["High"])
            low_value = _decimal_or_none(row["Low"])
            close_value = _decimal_or_none(row["Close"])
            volume_value = _decimal_or_none(row["Volume"])
            if (
                open_value is None
                or high_value is None
                or low_value is None
                or close_value is None
                or volume_value is None
            ):
                continue

            bars.append(
                ProviderBar(
                    symbol=symbol,
                    timestamp=trade_date,
                    open=open_value,
                    high=high_value,
                    low=low_value,
                    close=close_value,
                    volume=volume_value,
                    amount=None,
                )
            )
        return bars

    def fetch_intraday_bars(self, symbol: str, trade_date: date, timeframe: str) -> list[ProviderIntradayBar]:
        if timeframe != "1m":
            msg = f"Unsupported intraday timeframe for yfinance provider: {timeframe}"
            raise ValueError(msg)

        ticker = map_symbol_to_ticker(symbol, self._market)
        end_date = trade_date + timedelta(days=1)
        frame = _normalize_downloaded_frame(
            self._downloader(ticker, trade_date, end_date, interval="1m"),
            ticker,
        )
        if frame.empty or not _has_required_price_columns(frame):
            return []

        intraday_bars: list[ProviderIntradayBar] = []
        for timestamp, row in frame.iterrows():
            intraday_timestamp = _datetime_from_index_value(timestamp)
            if intraday_timestamp is None or intraday_timestamp.date() != trade_date:
                continue

            open_value = _decimal_or_none(row["Open"])
            high_value = _decimal_or_none(row["High"])
            low_value = _decimal_or_none(row["Low"])
            close_value = _decimal_or_none(row["Close"])
            volume_value = _decimal_or_none(row["Volume"])
            if (
                open_value is None
                or high_value is None
                or low_value is None
                or close_value is None
                or volume_value is None
            ):
                continue

            intraday_bars.append(
                ProviderIntradayBar(
                    symbol=symbol,
                    timestamp=intraday_timestamp,
                    open=open_value,
                    high=high_value,
                    low=low_value,
                    close=close_value,
                    volume=int(volume_value),
                    amount=None,
                    average_price=None,
                )
            )

        return intraday_bars

    def _download(self, ticker: str, start: date, end: date, interval: str | None = None) -> pd.DataFrame:
        import yfinance as yf

        download_options: dict[str, object] = {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "progress": False,
        }
        if interval is not None:
            download_options["interval"] = interval

        return yf.download(ticker, **download_options)


def _decimal_or_none(value: object) -> Decimal | None:
    try:
        decimal_value = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not decimal_value.is_finite():
        return None
    return decimal_value


def _datetime_from_index_value(value: object) -> datetime | None:
    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()
    if isinstance(value, datetime):
        return value
    return None


def _has_required_price_columns(frame: pd.DataFrame) -> bool:
    required_price_columns = {"Open", "High", "Low", "Close", "Volume"}
    return required_price_columns.issubset({str(column) for column in frame.columns})


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
