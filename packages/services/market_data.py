from datetime import date, timedelta

import pandas as pd
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from packages.analytics.indicators import calculate_ma, calculate_rsi
from packages.domain.models import DailyBar, Instrument, Market
from packages.providers.akshare_provider import AkShareProvider
from packages.providers.base import ProviderAdapter
from packages.providers.base import ProviderBar
from packages.providers.base import ProviderInstrument
from packages.providers.mock_provider import MockProvider
from packages.providers.tushare_provider import TushareProvider
from packages.providers.yfinance_provider import YFinanceProvider
from packages.services.platform_settings import get_effective_market_data_provider


def _provider() -> MockProvider:
    return MockProvider()


DEFAULT_RSI_WINDOW = 14


class MarketDataProviderError(RuntimeError):
    category = "provider_error"
    http_status_code = 502

    def __init__(self, provider_name: str, operation: str, original_error: Exception) -> None:
        self.provider_name = provider_name
        self.operation = operation
        self.original_error = original_error
        self.category = self.__class__.category
        self.http_status_code = self.__class__.http_status_code
        message = f"Market data provider '{provider_name}' failed while {operation}."
        super().__init__(message)


class MarketDataProviderTimeoutError(MarketDataProviderError):
    category = "timeout"
    http_status_code = 504


class MarketDataProviderRateLimitError(MarketDataProviderError):
    category = "rate_limited"
    http_status_code = 429


class MarketDataProviderUnavailableError(MarketDataProviderError):
    category = "unavailable"
    http_status_code = 503


class MarketDataProviderPayloadError(MarketDataProviderError):
    category = "malformed_payload"
    http_status_code = 502


def resolve_market_data_provider_name(provider_name: str | None = "mock") -> str:
    return get_effective_market_data_provider(provider_name)


def get_provider(provider_name: str = "mock") -> ProviderAdapter:
    normalized = resolve_market_data_provider_name(provider_name)
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


def _classify_provider_error(
    provider_name: str,
    operation: str,
    original_error: Exception,
) -> MarketDataProviderError:
    if isinstance(original_error, TimeoutError):
        return MarketDataProviderTimeoutError(provider_name, operation, original_error)
    if isinstance(original_error, ConnectionError):
        return MarketDataProviderUnavailableError(provider_name, operation, original_error)

    normalized_message = str(original_error).lower()
    if (
        "rate limit" in normalized_message
        or "too many requests" in normalized_message
        or "429" in normalized_message
    ):
        return MarketDataProviderRateLimitError(provider_name, operation, original_error)

    return MarketDataProviderError(provider_name, operation, original_error)


def _fetch_provider_bars(
    provider: ProviderAdapter,
    provider_name: str,
    symbol: str,
    timeframe: str,
    start: date,
    end: date,
) -> list[ProviderBar]:
    try:
        return provider.fetch_bars(symbol, timeframe, start, end)
    except ValueError:
        raise
    except Exception as error:
        raise _classify_provider_error(provider_name, "fetching bars", error) from error


def _fetch_provider_instruments(
    provider: ProviderAdapter,
    provider_name: str,
    market: str,
) -> list[ProviderInstrument]:
    try:
        return provider.fetch_instruments(market)
    except ValueError:
        raise
    except Exception as error:
        raise _classify_provider_error(provider_name, "fetching instruments", error) from error


def _latest_numeric_value_or_none(values: pd.Series) -> float | None:
    non_null_values = values.dropna()
    if non_null_values.empty:
        return None
    return float(non_null_values.iloc[-1])


def _calculate_latest_rsi_or_none(close_prices: pd.Series) -> float | None:
    if close_prices.empty:
        return None

    latest_rsi = _latest_numeric_value_or_none(calculate_rsi(close_prices))
    if latest_rsi is not None:
        return latest_rsi

    if len(close_prices) > DEFAULT_RSI_WINDOW:
        return 100.0

    return None


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


def _serialize_provider_bars(
    bars: list[ProviderBar],
    provider_name: str,
    operation: str,
) -> list[dict[str, float | str | None]]:
    try:
        return [serialize_bar(bar) for bar in bars]
    except Exception as error:
        raise MarketDataProviderPayloadError(provider_name, operation, error) from error


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
    effective_provider_name = resolve_market_data_provider_name(provider_name)
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

    provider = get_provider(effective_provider_name)
    bars = _fetch_provider_bars(
        provider,
        effective_provider_name,
        symbol,
        timeframe,
        start,
        end,
    )
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "source": effective_provider_name,
        "items": _serialize_provider_bars(
            bars,
            effective_provider_name,
            "serializing bars",
        ),
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
    close_prices = pd.Series([float(item["close"]) for item in items], dtype="float64")
    latest_ma = _latest_numeric_value_or_none(calculate_ma(close_prices, ma_window))
    latest_rsi = _calculate_latest_rsi_or_none(close_prices)

    return {
        "symbol": symbol,
        "as_of": str(items[-1]["timestamp"]) if items else None,
        "source": bars_payload["source"],
        "indicators": {
            "ma": latest_ma,
            "rsi": latest_rsi,
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
    effective_provider_name = resolve_market_data_provider_name(provider_name)
    provider = get_provider(effective_provider_name)
    instruments = _fetch_provider_instruments(provider, effective_provider_name, market)
    return {
        "market": market,
        "provider": effective_provider_name,
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
                "bars": _serialize_provider_bars(
                    _fetch_provider_bars(
                        provider,
                        effective_provider_name,
                        instrument.symbol,
                        timeframe,
                        start,
                        end,
                    ),
                    effective_provider_name,
                    "serializing snapshot bars",
                ),
            }
            for instrument in instruments
        ],
    }
