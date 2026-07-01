from datetime import date, timedelta

import pandas as pd
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from packages.analytics.indicators import calculate_ma, calculate_rsi
from packages.domain.models import DailyBar, Instrument, Market
from packages.providers.base import ProviderAdapter
from packages.providers.base import ProviderBar
from packages.providers.mock_provider import MockProvider
from packages.providers.yfinance_provider import YFinanceProvider
from packages.providers.akshare_provider import AkShareProvider
from packages.providers.tushare_provider import TushareProvider


def _provider() -> MockProvider:
    return MockProvider()


from packages.services.platform_settings import get_effective_market_data_provider


def get_provider(provider_name: str = "mock") -> ProviderAdapter:
    normalized = get_effective_market_data_provider(provider_name)
    if normalized == "mock":
        return MockProvider()
    if normalized == "yfinance":
        return YFinanceProvider()
    if normalized == "akshare":
        return AkShareProvider()
    if normalized == "tushare":
        return TushareProvider()
    msg = f"Unsupported market data provider: {provider_name}"
    raise ValueError(msg)


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
    provider_name: str = "mock",
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

    provider = get_provider(provider_name)
    bars = provider.fetch_bars(symbol, timeframe, start, end)
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "source": provider_name.lower(),
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


def get_latest_bar_payload(
    symbol: str,
    session: Session | None = None,
    provider_name: str = "mock",
) -> dict[str, object]:
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

    end = date.today()
    start = end - timedelta(days=7)
    fallback = get_bars_payload(
        symbol,
        "1d",
        start,
        end,
        session=session,
        provider_name=provider_name,
    )
    items = fallback["items"]
    return {
        "symbol": symbol,
        "timeframe": "1d",
        "source": fallback["source"],
        "item": items[-1] if items else None,
    }


def get_latest_bars_batch_payload(
    symbols: list[str],
    session: Session | None = None,
    provider_name: str = "mock",
) -> dict[str, object]:
    items: list[dict[str, object]] = []
    sources: set[str] = set()

    for symbol in symbols:
        payload = get_latest_bar_payload(symbol, session=session, provider_name=provider_name)
        source = str(payload["source"])
        sources.add(source)
        items.append(
            {
                "symbol": symbol,
                "source": source,
                "item": payload["item"],
            }
        )

    return {
        "source": sources.pop() if len(sources) == 1 else "mixed",
        "items": items,
    }


def get_market_snapshot(
    market: str,
    start: date,
    end: date,
    timeframe: str = "1d",
    provider_name: str = "mock",
) -> dict[str, object]:
    provider = get_provider(provider_name)
    instruments = provider.fetch_instruments(market)
    return {
        "market": market,
        "provider": provider_name.lower(),
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
