from datetime import date, timedelta
from decimal import Decimal

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
NO_DAILY_BARS_REASON = "No daily bars were available for the requested symbol/date range."
DEFAULT_INTRADAY_TIMEFRAME = "1m"
INTRADAY_UNSUPPORTED_REASON = "The selected provider does not support verified minute bars in this backend."
DEFAULT_MARKET_DEPTH_LEVELS = 5
DEFAULT_LARGE_ORDER_THRESHOLD_AMOUNT = Decimal("1000000")
MARKET_DEPTH_UNSUPPORTED_REASON = "The selected provider does not expose verified market depth data in this backend."
RECENT_TRADES_UNSUPPORTED_REASON = "Recent trades are not normalized or verified by this backend yet."
LARGE_ORDERS_UNSUPPORTED_REASON = "Large order detection requires verified recent trades, which are unavailable."
FUND_FLOW_UNSUPPORTED_REASON = "Fund-flow data is not normalized or verified by this backend yet."

MARKET_DEPTH_PROVIDER_CAPABILITIES = {
    "mock": {
        "order_book": False,
        "recent_trades": False,
        "large_orders": False,
        "fund_flow": False,
        "reason": "Mock provider does not expose verified real market depth data.",
    },
    "yfinance": {
        "order_book": False,
        "recent_trades": False,
        "large_orders": False,
        "fund_flow": False,
        "reason": "YFinance provider does not expose verified level-2 market depth in this backend.",
    },
    "akshare": {
        "order_book": False,
        "recent_trades": False,
        "large_orders": False,
        "fund_flow": False,
        "reason": "AkShare depth data is not normalized or verified by this backend yet.",
    },
    "tushare": {
        "order_book": False,
        "recent_trades": False,
        "large_orders": False,
        "fund_flow": False,
        "reason": "Tushare depth/trade/fund-flow access is not normalized or permission-verified yet.",
    },
}


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


def resolve_market_data_provider_name(provider_name: str | None = None) -> str:
    return get_effective_market_data_provider(provider_name)


def get_provider(provider_name: str | None = None) -> ProviderAdapter:
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


def _normalize_requested_provider_name(provider_name: str | None) -> str | None:
    if provider_name is None:
        return None
    normalized = provider_name.strip().lower()
    return normalized or None


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


def _build_data_availability_metadata(items: list[object]) -> dict[str, str | None]:
    if items:
        return {
            "status": "ok",
            "no_data_reason": None,
        }
    return {
        "status": "no_data",
        "no_data_reason": NO_DAILY_BARS_REASON,
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
    provider_name: str | None = None,
) -> dict[str, object]:
    requested_provider_name = _normalize_requested_provider_name(provider_name)
    effective_provider_name = resolve_market_data_provider_name(provider_name)
    if timeframe == "1d" and session is not None:
        try:
            db_bars = _fetch_daily_bars_from_database(symbol, start, end, session)
        except SQLAlchemyError:
            db_bars = []
        if db_bars:
            serialized_db_bars = [serialize_daily_bar(bar) for bar in db_bars]
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "source": "database",
                "provider": effective_provider_name,
                "requested_provider": requested_provider_name,
                "effective_provider": effective_provider_name,
                "items": serialized_db_bars,
                **_build_data_availability_metadata(serialized_db_bars),
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
    serialized_provider_bars = _serialize_provider_bars(
        bars,
        effective_provider_name,
        "serializing bars",
    )
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "source": effective_provider_name,
        "provider": effective_provider_name,
        "requested_provider": requested_provider_name,
        "effective_provider": effective_provider_name,
        "items": serialized_provider_bars,
        **_build_data_availability_metadata(serialized_provider_bars),
    }


def get_intraday_bars_payload(
    symbol: str,
    trade_date: date,
    timeframe: str = DEFAULT_INTRADAY_TIMEFRAME,
    session: Session | None = None,
    provider_name: str | None = None,
) -> dict[str, object]:
    if timeframe != DEFAULT_INTRADAY_TIMEFRAME:
        msg = f"Unsupported intraday timeframe: {timeframe}. Only {DEFAULT_INTRADAY_TIMEFRAME} is supported."
        raise ValueError(msg)

    requested_provider_name = _normalize_requested_provider_name(provider_name)
    effective_provider_name = resolve_market_data_provider_name(provider_name)

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "date": trade_date.isoformat(),
        "source": "none",
        "provider": effective_provider_name,
        "requested_provider": requested_provider_name,
        "effective_provider": effective_provider_name,
        "status": "degraded",
        "previous_close": None,
        "items": [],
        "availability": {
            "status": "degraded",
            "reason": INTRADAY_UNSUPPORTED_REASON,
            "is_realtime": False,
            "is_delayed": False,
            "delay_minutes": None,
        },
    }


def get_market_depth_payload(
    symbol: str,
    provider_name: str | None = None,
    depth_levels: int = DEFAULT_MARKET_DEPTH_LEVELS,
    large_order_threshold_amount: Decimal | None = None,
) -> dict[str, object]:
    requested_provider_name = _normalize_requested_provider_name(provider_name)
    effective_provider_name = resolve_market_data_provider_name(provider_name)
    provider_capabilities = MARKET_DEPTH_PROVIDER_CAPABILITIES.get(effective_provider_name)
    if provider_capabilities is None:
        msg = f"Unsupported market data provider: {provider_name}"
        raise ValueError(msg)

    threshold_amount = large_order_threshold_amount or DEFAULT_LARGE_ORDER_THRESHOLD_AMOUNT
    provider_reason = str(provider_capabilities["reason"])
    capabilities = {
        "order_book": bool(provider_capabilities["order_book"]),
        "recent_trades": bool(provider_capabilities["recent_trades"]),
        "large_orders": bool(provider_capabilities["large_orders"]),
        "fund_flow": bool(provider_capabilities["fund_flow"]),
    }

    return {
        "symbol": symbol,
        "source": "none",
        "provider": effective_provider_name,
        "requested_provider": requested_provider_name,
        "effective_provider": effective_provider_name,
        "status": "degraded",
        "as_of": None,
        "is_realtime": False,
        "is_delayed": False,
        "delay_minutes": None,
        "order_book": {
            "status": "degraded",
            "reason": provider_reason,
            "as_of": None,
            "depth_levels": depth_levels,
            "bids": [],
            "asks": [],
        },
        "recent_trades": {
            "status": "degraded",
            "reason": RECENT_TRADES_UNSUPPORTED_REASON,
            "as_of": None,
            "items": [],
        },
        "large_orders": {
            "status": "degraded",
            "reason": LARGE_ORDERS_UNSUPPORTED_REASON,
            "threshold_amount": float(threshold_amount),
            "threshold_volume": None,
            "currency": None,
            "as_of": None,
            "items": [],
        },
        "fund_flow": {
            "status": "degraded",
            "reason": FUND_FLOW_UNSUPPORTED_REASON,
            "as_of": None,
            "currency": None,
            "net_inflow": None,
            "main_net_inflow": None,
            "retail_net_inflow": None,
            "source_definition": None,
        },
        "availability": {
            "status": "degraded",
            "reason": MARKET_DEPTH_UNSUPPORTED_REASON,
            "capabilities": capabilities,
        },
    }


def get_indicator_payload(
    symbol: str,
    start: date,
    end: date,
    ma_window: int,
    session: Session | None = None,
    provider_name: str | None = None,
) -> dict[str, object]:
    bars_payload = get_bars_payload(
        symbol,
        "1d",
        start,
        end,
        session=session,
        provider_name=provider_name,
    )
    items = bars_payload["items"]
    close_prices = pd.Series([float(item["close"]) for item in items], dtype="float64")
    latest_ma = _latest_numeric_value_or_none(calculate_ma(close_prices, ma_window))
    latest_rsi = _calculate_latest_rsi_or_none(close_prices)

    return {
        "symbol": symbol,
        "as_of": str(items[-1]["timestamp"]) if items else None,
        "source": bars_payload["source"],
        "provider": bars_payload.get("provider"),
        "requested_provider": bars_payload.get("requested_provider"),
        "effective_provider": bars_payload.get("effective_provider"),
        "status": bars_payload.get("status"),
        "no_data_reason": bars_payload.get("no_data_reason"),
        "indicators": {
            "ma": latest_ma,
            "rsi": latest_rsi,
        },
    }


def get_latest_bar_payload(
    symbol: str,
    session: Session | None = None,
    provider_name: str | None = None,
) -> dict[str, object]:
    requested_provider_name = _normalize_requested_provider_name(provider_name)
    effective_provider_name = resolve_market_data_provider_name(provider_name)
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
            serialized_db_bar = serialize_daily_bar(db_bar)
            return {
                "symbol": symbol,
                "timeframe": "1d",
                "source": "database",
                "provider": effective_provider_name,
                "requested_provider": requested_provider_name,
                "effective_provider": effective_provider_name,
                "item": serialized_db_bar,
                "status": "ok",
                "no_data_reason": None,
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
    latest_item = items[-1] if items else None
    return {
        "symbol": symbol,
        "timeframe": "1d",
        "source": fallback["source"],
        "provider": fallback.get("provider"),
        "requested_provider": fallback.get("requested_provider"),
        "effective_provider": fallback.get("effective_provider"),
        "item": latest_item,
        "status": "ok" if latest_item is not None else "no_data",
        "no_data_reason": None if latest_item is not None else fallback.get("no_data_reason", NO_DAILY_BARS_REASON),
    }


def get_latest_bars_batch_payload(
    symbols: list[str],
    session: Session | None = None,
    provider_name: str | None = None,
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
                "provider": payload.get("provider"),
                "requested_provider": payload.get("requested_provider"),
                "effective_provider": payload.get("effective_provider"),
                "status": payload.get("status"),
                "no_data_reason": payload.get("no_data_reason"),
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
    provider_name: str | None = None,
) -> dict[str, object]:
    requested_provider_name = _normalize_requested_provider_name(provider_name)
    effective_provider_name = resolve_market_data_provider_name(provider_name)
    provider = get_provider(effective_provider_name)
    instruments = _fetch_provider_instruments(provider, effective_provider_name, market)
    return {
        "market": market,
        "provider": effective_provider_name,
        "requested_provider": requested_provider_name,
        "effective_provider": effective_provider_name,
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
