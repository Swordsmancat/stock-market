from datetime import date

import pandas as pd

from packages.analytics.indicators import calculate_ma, calculate_rsi
from packages.providers.base import ProviderBar
from packages.providers.mock_provider import MockProvider


def _provider() -> MockProvider:
    return MockProvider()


def serialize_bar(bar: ProviderBar) -> dict[str, float | str | None]:
    return {
        "timestamp": bar.timestamp.isoformat(),
        "open": float(bar.open),
        "high": float(bar.high),
        "low": float(bar.low),
        "close": float(bar.close),
        "volume": float(bar.volume),
        "amount": float(bar.amount) if bar.amount is not None else None,
    }


def get_bars_payload(symbol: str, timeframe: str, start: date, end: date) -> dict[str, object]:
    bars = _provider().fetch_bars(symbol, timeframe, start, end)
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "items": [serialize_bar(bar) for bar in bars],
    }


def get_indicator_payload(symbol: str, start: date, end: date, ma_window: int) -> dict[str, object]:
    bars = _provider().fetch_bars(symbol, "1d", start, end)
    close = pd.Series([float(bar.close) for bar in bars])
    latest_ma = calculate_ma(close, ma_window).dropna().iloc[-1]
    rsi_series = calculate_rsi(close)
    latest_rsi = rsi_series.dropna().iloc[-1] if not rsi_series.dropna().empty else 100.0

    return {
        "symbol": symbol,
        "as_of": bars[-1].timestamp.isoformat(),
        "indicators": {
            "ma": float(latest_ma),
            "rsi": float(latest_rsi),
        },
    }


def get_market_snapshot(
    market: str,
    start: date,
    end: date,
    timeframe: str = "1d",
) -> dict[str, object]:
    provider = _provider()
    instruments = provider.fetch_instruments(market)
    return {
        "market": market,
        "timeframe": timeframe,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "instrument_count": len(instruments),
        "instruments": [
            {
                "symbol": instrument.symbol,
                "name": instrument.name,
                "exchange": instrument.exchange,
                "asset_type": instrument.asset_type,
                "currency": instrument.currency,
                "bars": [
                    serialize_bar(bar)
                    for bar in provider.fetch_bars(instrument.symbol, timeframe, start, end)
                ],
            }
            for instrument in instruments
        ],
    }
