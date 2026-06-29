from datetime import date

import pandas as pd
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from packages.analytics.indicators import calculate_ma, calculate_rsi
from packages.domain.models import DailyBar, Instrument, Market
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


def serialize_daily_bar(bar: DailyBar) -> dict[str, float | str | None]:
    return {
        "timestamp": bar.trade_date.isoformat(),
        "open": float(bar.open),
        "high": float(bar.high),
        "low": float(bar.low),
        "close": float(bar.close),
        "volume": float(bar.volume),
        "amount": float(bar.amount) if bar.amount is not None else None,
    }


def _fetch_daily_bars_from_database(
    symbol: str,
    start: date,
    end: date,
    session: Session,
) -> list[DailyBar]:
    return (
        session.query(DailyBar)
        .join(Instrument, DailyBar.instrument_id == Instrument.id)
        .join(Market, Instrument.market_id == Market.id)
        .filter(Instrument.symbol == symbol)
        .filter(DailyBar.trade_date >= start)
        .filter(DailyBar.trade_date <= end)
        .order_by(DailyBar.trade_date)
        .all()
    )


def get_bars_payload(
    symbol: str,
    timeframe: str,
    start: date,
    end: date,
    session: Session | None = None,
) -> dict[str, object]:
    if timeframe == "1d" and session is not None:
        try:
            db_bars = _fetch_daily_bars_from_database(symbol, start, end, session)
        except SQLAlchemyError:
            db_bars = []
        if db_bars:
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "source": "database",
                "items": [serialize_daily_bar(bar) for bar in db_bars],
            }

    bars = _provider().fetch_bars(symbol, timeframe, start, end)
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "source": "mock",
        "items": [serialize_bar(bar) for bar in bars],
    }


def get_indicator_payload(
    symbol: str,
    start: date,
    end: date,
    ma_window: int,
    session: Session | None = None,
) -> dict[str, object]:
    bars_payload = get_bars_payload(symbol, "1d", start, end, session=session)
    items = bars_payload["items"]
    close = pd.Series([float(item["close"]) for item in items])
    latest_ma = calculate_ma(close, ma_window).dropna().iloc[-1]
    rsi_series = calculate_rsi(close)
    latest_rsi = rsi_series.dropna().iloc[-1] if not rsi_series.dropna().empty else 100.0

    return {
        "symbol": symbol,
        "as_of": str(items[-1]["timestamp"]),
        "source": bars_payload["source"],
        "indicators": {
            "ma": float(latest_ma),
            "rsi": float(latest_rsi),
        },
    }


def get_latest_bar_payload(symbol: str, session: Session | None = None) -> dict[str, object]:
    if session is not None:
        try:
            db_bar = (
                session.query(DailyBar)
                .join(Instrument, DailyBar.instrument_id == Instrument.id)
                .filter(Instrument.symbol == symbol)
                .order_by(DailyBar.trade_date.desc())
                .first()
            )
        except SQLAlchemyError:
            db_bar = None
        if db_bar is not None:
            return {
                "symbol": symbol,
                "timeframe": "1d",
                "source": "database",
                "item": serialize_daily_bar(db_bar),
            }

    fallback = get_bars_payload(symbol, "1d", date(2026, 1, 1), date(2026, 1, 1))
    return {
        "symbol": symbol,
        "timeframe": "1d",
        "source": fallback["source"],
        "item": fallback["items"][-1],
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
