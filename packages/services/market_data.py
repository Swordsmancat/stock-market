from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pandas as pd
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from packages.analytics.indicators import calculate_ma, calculate_rsi
from packages.domain.models import DailyBar, Instrument, IntradayMinuteCacheEntry, Market, MinuteBar
from packages.providers.akshare_provider import AkShareProvider
from packages.providers.base import ProviderAdapter
from packages.providers.base import ProviderBar
from packages.providers.base import ProviderFundFlow
from packages.providers.base import ProviderInstrument
from packages.providers.base import ProviderIntradayBar
from packages.providers.base import ProviderMarketDepthSnapshot
from packages.providers.base import ProviderOrderBookLevel
from packages.providers.base import ProviderRecentTrade
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
INTRADAY_NO_DATA_REASON = "No verified minute bars were returned for the requested symbol and trade date."
INTRADAY_FUTURE_NO_DATA_REASON = "The requested date is in the future; no verified stock-market minute session is available yet."
INTRADAY_KNOWN_HOLIDAY_NO_DATA_REASON = "The requested date is a recognized market holiday for this provider/symbol; no verified stock-market minute session is expected."
INTRADAY_WEEKEND_NO_DATA_REASON = "The requested date falls on a weekend; no verified stock-market minute session is expected."
INTRADAY_CACHE_UNAVAILABLE_REASON = "Persistent intraday cache was unavailable; provider data was returned without cache reuse."
INTRADAY_PREVIOUS_CLOSE_LOOKBACK_DAYS = 10
INTRADAY_CACHE_SOURCE = "provider_verified"
INTRADAY_MARKET_META = {
    "US": {"name": "US Stock", "timezone": "America/New_York", "currency": "USD"},
}
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


@dataclass(frozen=True)
class IntradayCacheLookup:
    status: str
    items: list[dict[str, float | int | str | None]]
    entry: IntradayMinuteCacheEntry | None = None
    reason: str | None = None


@dataclass(frozen=True)
class IntradayCacheWriteResult:
    status: str
    fetched_at: str | None
    cached_at: str | None
    reason: str | None = None


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


def _fetch_provider_intraday_bars(
    provider: ProviderAdapter,
    provider_name: str,
    symbol: str,
    trade_date: date,
    timeframe: str,
) -> list[ProviderIntradayBar]:
    fetch_intraday_bars = getattr(provider, "fetch_intraday_bars", None)
    if not callable(fetch_intraday_bars):
        return []

    try:
        return fetch_intraday_bars(symbol, trade_date, timeframe)
    except ValueError:
        raise
    except Exception as error:
        raise _classify_provider_error(provider_name, "fetching intraday bars", error) from error


def _provider_supports_verified_intraday_bars(provider: ProviderAdapter) -> bool:
    return callable(getattr(provider, "fetch_intraday_bars", None))


def _fetch_provider_market_depth(
    provider: ProviderAdapter,
    provider_name: str,
    symbol: str,
    depth_levels: int,
) -> ProviderMarketDepthSnapshot | None:
    fetch_market_depth = getattr(provider, "fetch_market_depth", None)
    if not callable(fetch_market_depth):
        return None

    try:
        return fetch_market_depth(symbol, depth_levels)
    except ValueError:
        raise
    except Exception as error:
        raise _classify_provider_error(provider_name, "fetching market depth", error) from error


def _provider_supports_verified_market_depth(provider: ProviderAdapter) -> bool:
    return callable(getattr(provider, "fetch_market_depth", None))


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


def serialize_intraday_bar(bar: ProviderIntradayBar) -> dict[str, float | int | str | None]:
    close_price = float(bar.close)
    return {
        "timestamp": _normalize_intraday_timestamp(bar.timestamp).isoformat(),
        "open": float(bar.open),
        "high": float(bar.high),
        "low": float(bar.low),
        "close": close_price,
        "price": close_price,
        "average_price": float(bar.average_price) if bar.average_price is not None else None,
        "volume": bar.volume,
        "amount": float(bar.amount) if bar.amount is not None else None,
    }


def serialize_cached_intraday_bar(bar: MinuteBar) -> dict[str, float | int | str | None]:
    close_price = float(bar.close)
    return {
        "timestamp": _normalize_intraday_timestamp(bar.ts).isoformat(),
        "open": float(bar.open),
        "high": float(bar.high),
        "low": float(bar.low),
        "close": close_price,
        "price": close_price,
        "average_price": None,
        "volume": int(bar.volume),
        "amount": float(bar.amount) if bar.amount is not None else None,
    }


def _serialize_provider_intraday_bars(
    bars: list[ProviderIntradayBar],
    provider_name: str,
) -> list[dict[str, float | int | str | None]]:
    try:
        return [serialize_intraday_bar(bar) for bar in bars]
    except Exception as error:
        raise MarketDataProviderPayloadError(provider_name, "serializing intraday bars", error) from error


def serialize_order_book_level(level: ProviderOrderBookLevel) -> dict[str, float | int | None]:
    return {
        "price": float(level.price),
        "volume": float(level.volume),
        "amount": float(level.amount) if level.amount is not None else None,
        "order_count": level.order_count,
    }


def serialize_recent_trade(trade: ProviderRecentTrade) -> dict[str, float | str | None]:
    amount = trade.amount if trade.amount is not None else trade.price * trade.volume
    return {
        "timestamp": trade.timestamp.isoformat(),
        "price": float(trade.price),
        "volume": float(trade.volume),
        "amount": float(amount),
        "side": trade.side,
    }


def serialize_fund_flow(fund_flow: ProviderFundFlow | None) -> dict[str, float | str | None]:
    if fund_flow is None:
        return {
            "currency": None,
            "net_inflow": None,
            "main_net_inflow": None,
            "retail_net_inflow": None,
            "source_definition": None,
        }

    return {
        "currency": fund_flow.currency,
        "net_inflow": float(fund_flow.net_inflow) if fund_flow.net_inflow is not None else None,
        "main_net_inflow": float(fund_flow.main_net_inflow) if fund_flow.main_net_inflow is not None else None,
        "retail_net_inflow": float(fund_flow.retail_net_inflow) if fund_flow.retail_net_inflow is not None else None,
        "source_definition": fund_flow.source_definition,
    }


def _serialize_provider_market_depth_snapshot(
    snapshot: ProviderMarketDepthSnapshot,
    provider_name: str,
) -> dict[str, object]:
    try:
        return {
            "bids": [serialize_order_book_level(level) for level in snapshot.bids],
            "asks": [serialize_order_book_level(level) for level in snapshot.asks],
            "recent_trades": [serialize_recent_trade(trade) for trade in snapshot.recent_trades],
            "fund_flow": serialize_fund_flow(snapshot.fund_flow),
        }
    except Exception as error:
        raise MarketDataProviderPayloadError(provider_name, "serializing market depth", error) from error


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
    provider = get_provider(effective_provider_name)
    database_previous_close = _get_previous_close_reference_from_database(
        symbol=symbol,
        trade_date=trade_date,
        session=session,
    )

    if not _provider_supports_verified_intraday_bars(provider):
        return _build_unsupported_intraday_payload(
            symbol=symbol,
            trade_date=trade_date,
            timeframe=timeframe,
            requested_provider_name=requested_provider_name,
            effective_provider_name=effective_provider_name,
            previous_close=database_previous_close,
        )

    if _is_future_trade_date(trade_date):
        return _build_intraday_no_data_payload(
            symbol=symbol,
            trade_date=trade_date,
            timeframe=timeframe,
            requested_provider_name=requested_provider_name,
            effective_provider_name=effective_provider_name,
            previous_close=database_previous_close,
            reason=INTRADAY_FUTURE_NO_DATA_REASON,
            source="none",
        )

    if _is_weekend_trade_date(trade_date):
        return _build_intraday_no_data_payload(
            symbol=symbol,
            trade_date=trade_date,
            timeframe=timeframe,
            requested_provider_name=requested_provider_name,
            effective_provider_name=effective_provider_name,
            previous_close=database_previous_close,
            reason=INTRADAY_WEEKEND_NO_DATA_REASON,
            source="none",
        )

    if _is_known_intraday_market_holiday(effective_provider_name, symbol, trade_date):
        return _build_intraday_no_data_payload(
            symbol=symbol,
            trade_date=trade_date,
            timeframe=timeframe,
            requested_provider_name=requested_provider_name,
            effective_provider_name=effective_provider_name,
            previous_close=database_previous_close,
            reason=INTRADAY_KNOWN_HOLIDAY_NO_DATA_REASON,
            source="none",
        )

    session_status = _classify_regular_intraday_session_status(trade_date)
    cache_lookup = _get_intraday_cache_lookup(
        symbol=symbol,
        trade_date=trade_date,
        timeframe=timeframe,
        session=session,
        provider_name=effective_provider_name,
        session_status=session_status,
    )
    if cache_lookup.status == "hit":
        return _build_intraday_ok_payload(
            symbol=symbol,
            trade_date=trade_date,
            timeframe=timeframe,
            requested_provider_name=requested_provider_name,
            effective_provider_name=effective_provider_name,
            previous_close=database_previous_close,
            items=cache_lookup.items,
            source="cache",
            freshness_status="closed",
            freshness_reason=None,
            cache_status="hit",
            fetched_at=cache_lookup.entry.fetched_at.isoformat() if cache_lookup.entry is not None else None,
            cached_at=cache_lookup.entry.cached_at.isoformat() if cache_lookup.entry is not None else None,
            session_status=session_status,
        )

    previous_close = _get_previous_close_reference(
        symbol=symbol,
        trade_date=trade_date,
        session=session,
        provider_name=effective_provider_name,
    )
    intraday_bars = _fetch_provider_intraday_bars(
        provider,
        effective_provider_name,
        symbol,
        trade_date,
        timeframe,
    )
    serialized_intraday_bars = _serialize_provider_intraday_bars(intraday_bars, effective_provider_name)
    if not serialized_intraday_bars:
        return _build_intraday_no_data_payload(
            symbol=symbol,
            trade_date=trade_date,
            timeframe=timeframe,
            requested_provider_name=requested_provider_name,
            effective_provider_name=effective_provider_name,
            previous_close=previous_close,
            reason=INTRADAY_NO_DATA_REASON,
            cache_status=_provider_empty_intraday_cache_status(cache_lookup.status, session_status),
        )

    cache_write = _persist_intraday_cache_bars(
        symbol=symbol,
        trade_date=trade_date,
        timeframe=timeframe,
        session=session,
        provider_name=effective_provider_name,
        session_status=session_status,
        bars=intraday_bars,
        cache_lookup_status=cache_lookup.status,
    )
    return _build_intraday_ok_payload(
        symbol=symbol,
        trade_date=trade_date,
        timeframe=timeframe,
        requested_provider_name=requested_provider_name,
        effective_provider_name=effective_provider_name,
        previous_close=previous_close,
        items=serialized_intraday_bars,
        source="provider",
        freshness_status="fresh",
        freshness_reason=cache_write.reason,
        cache_status=_provider_intraday_cache_status(cache_lookup.status, cache_write.status, session_status),
        fetched_at=cache_write.fetched_at,
        cached_at=cache_write.cached_at,
        session_status=session_status,
    )


def _build_intraday_no_data_payload(
    *,
    symbol: str,
    trade_date: date,
    timeframe: str,
    requested_provider_name: str | None,
    effective_provider_name: str,
    previous_close: float | None,
    reason: str,
    source: str = "provider",
    cache_status: str | None = None,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "date": trade_date.isoformat(),
        "source": source,
        "provider": effective_provider_name,
        "requested_provider": requested_provider_name,
        "effective_provider": effective_provider_name,
        "status": "no_data",
        "previous_close": previous_close,
        "items": [],
        "availability": {
            "status": "no_data",
            "reason": reason,
            "is_realtime": False,
            "is_delayed": True,
            "delay_minutes": None,
        },
        "freshness": _build_intraday_freshness_metadata(
            status=_intraday_freshness_status_for_reason(reason),
            reason=reason,
            data_as_of=trade_date.isoformat(),
            cache_status=cache_status or _intraday_cache_status_for_reason(reason),
        ),
        "session": _build_intraday_session_metadata(
            provider_name=effective_provider_name,
            symbol=symbol,
            trade_date=trade_date,
            status=_intraday_session_status_for_reason(reason, trade_date),
            reason=reason,
        ),
    }


def _build_intraday_ok_payload(
    *,
    symbol: str,
    trade_date: date,
    timeframe: str,
    requested_provider_name: str | None,
    effective_provider_name: str,
    previous_close: float | None,
    items: list[dict[str, float | int | str | None]],
    source: str,
    freshness_status: str,
    freshness_reason: str | None,
    cache_status: str,
    fetched_at: str | None,
    cached_at: str | None,
    session_status: str,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "date": trade_date.isoformat(),
        "source": source,
        "provider": effective_provider_name,
        "requested_provider": requested_provider_name,
        "effective_provider": effective_provider_name,
        "status": "ok",
        "previous_close": previous_close,
        "items": items,
        "availability": {
            "status": "ok",
            "reason": None,
            "is_realtime": False,
            "is_delayed": True,
            "delay_minutes": None,
        },
        "freshness": _build_intraday_freshness_metadata(
            status=freshness_status,
            reason=freshness_reason,
            data_as_of=_latest_intraday_item_timestamp(items),
            cache_status=cache_status,
            fetched_at=fetched_at,
            cached_at=cached_at,
        ),
        "session": _build_intraday_session_metadata(
            provider_name=effective_provider_name,
            symbol=symbol,
            trade_date=trade_date,
            status=session_status,
            reason=None,
        ),
    }


def _is_weekend_trade_date(trade_date: date) -> bool:
    return trade_date.weekday() >= 5


def _is_future_trade_date(trade_date: date) -> bool:
    return trade_date > date.today()


def _is_known_intraday_market_holiday(provider_name: str, symbol: str, trade_date: date) -> bool:
    if provider_name != "yfinance" or not _symbol_looks_like_us_equity(symbol):
        return False
    return _is_us_equity_fixed_holiday_or_observed(trade_date)


def _symbol_looks_like_us_equity(symbol: str) -> bool:
    normalized_symbol = symbol.strip().upper()
    return 1 <= len(normalized_symbol) <= 5 and normalized_symbol.isalpha()


def _is_us_equity_fixed_holiday_or_observed(trade_date: date) -> bool:
    fixed_us_equity_holidays = (
        (1, 1),
        (6, 19),
        (7, 4),
        (12, 25),
    )
    for holiday_month, holiday_day in fixed_us_equity_holidays:
        holiday_date = date(trade_date.year, holiday_month, holiday_day)
        if trade_date in {holiday_date, _observed_fixed_holiday_date(holiday_date)}:
            return True

    movable_us_equity_holidays = {
        _nth_weekday_of_month(trade_date.year, 1, weekday=0, occurrence=3),
        _nth_weekday_of_month(trade_date.year, 2, weekday=0, occurrence=3),
        _last_weekday_of_month(trade_date.year, 5, weekday=0),
        _nth_weekday_of_month(trade_date.year, 9, weekday=0, occurrence=1),
        _nth_weekday_of_month(trade_date.year, 11, weekday=3, occurrence=4),
        _easter_sunday(trade_date.year) - timedelta(days=2),
    }
    return trade_date in movable_us_equity_holidays


def _observed_fixed_holiday_date(holiday_date: date) -> date:
    if holiday_date.weekday() == 5:
        return holiday_date - timedelta(days=1)
    if holiday_date.weekday() == 6:
        return holiday_date + timedelta(days=1)
    return holiday_date


def _nth_weekday_of_month(year: int, month: int, *, weekday: int, occurrence: int) -> date:
    first_day_of_month = date(year, month, 1)
    days_until_weekday = (weekday - first_day_of_month.weekday()) % 7
    return first_day_of_month + timedelta(days=days_until_weekday + 7 * (occurrence - 1))


def _last_weekday_of_month(year: int, month: int, *, weekday: int) -> date:
    first_day_of_next_month = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    candidate_date = first_day_of_next_month - timedelta(days=1)
    while candidate_date.weekday() != weekday:
        candidate_date -= timedelta(days=1)
    return candidate_date


def _easter_sunday(year: int) -> date:
    golden_year = year % 19
    century = year // 100
    year_in_century = year % 100
    skipped_leap_years = century // 4
    century_remainder = century % 4
    correction = (century + 8) // 25
    moon_correction = (century - correction + 1) // 3
    epact = (19 * golden_year + century - skipped_leap_years - moon_correction + 15) % 30
    year_in_century_leaps = year_in_century // 4
    year_in_century_remainder = year_in_century % 4
    weekday_correction = (32 + 2 * century_remainder + 2 * year_in_century_leaps - epact - year_in_century_remainder) % 7
    month_offset = (golden_year + 11 * epact + 22 * weekday_correction) // 451
    month = (epact + weekday_correction - 7 * month_offset + 114) // 31
    day = ((epact + weekday_correction - 7 * month_offset + 114) % 31) + 1
    return date(year, month, day)


def _build_unsupported_intraday_payload(
    *,
    symbol: str,
    trade_date: date,
    timeframe: str,
    requested_provider_name: str | None,
    effective_provider_name: str,
    previous_close: float | None,
) -> dict[str, object]:
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "date": trade_date.isoformat(),
        "source": "none",
        "provider": effective_provider_name,
        "requested_provider": requested_provider_name,
        "effective_provider": effective_provider_name,
        "status": "degraded",
        "previous_close": previous_close,
        "items": [],
        "availability": {
            "status": "degraded",
            "reason": INTRADAY_UNSUPPORTED_REASON,
            "is_realtime": False,
            "is_delayed": False,
            "delay_minutes": None,
        },
        "freshness": _build_intraday_freshness_metadata(
            status="unsupported",
            reason=INTRADAY_UNSUPPORTED_REASON,
            data_as_of=trade_date.isoformat(),
            cache_status="skipped",
        ),
        "session": _build_intraday_session_metadata(
            provider_name=effective_provider_name,
            symbol=symbol,
            trade_date=trade_date,
            status="unsupported_market",
            reason=INTRADAY_UNSUPPORTED_REASON,
        ),
    }


def _build_intraday_freshness_metadata(
    *,
    status: str,
    reason: str | None,
    data_as_of: str | None,
    cache_status: str,
    fetched_at: str | None = None,
    cached_at: str | None = None,
) -> dict[str, object]:
    return {
        "status": status,
        "reason": reason,
        "data_as_of": data_as_of,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "fetched_at": fetched_at,
        "cached_at": cached_at,
        "cache_status": cache_status,
        "max_age_seconds": None,
    }


def _build_intraday_session_metadata(
    *,
    provider_name: str,
    symbol: str,
    trade_date: date,
    status: str,
    reason: str | None,
) -> dict[str, object]:
    return {
        "market": _infer_intraday_market(provider_name, symbol),
        "timezone": _infer_intraday_timezone(provider_name, symbol),
        "trading_date": trade_date.isoformat(),
        "status": status,
        "reason": reason,
    }


def _latest_intraday_item_timestamp(items: list[dict[str, float | int | str | None]]) -> str | None:
    if not items:
        return None
    latest_timestamp = items[-1].get("timestamp")
    return str(latest_timestamp) if latest_timestamp is not None else None


def _get_intraday_cache_lookup(
    *,
    symbol: str,
    trade_date: date,
    timeframe: str,
    session: Session | None,
    provider_name: str,
    session_status: str,
) -> IntradayCacheLookup:
    if session_status != "closed_session":
        return IntradayCacheLookup(status="skipped", items=[], reason=None)
    if session is None or not _can_use_persistent_intraday_cache(provider_name, symbol):
        return IntradayCacheLookup(status="unavailable", items=[], reason=INTRADAY_CACHE_UNAVAILABLE_REASON)

    normalized_symbol = _normalize_intraday_cache_symbol(symbol)
    try:
        cache_entry = (
            session.query(IntradayMinuteCacheEntry)
            .filter(IntradayMinuteCacheEntry.provider == provider_name)
            .filter(IntradayMinuteCacheEntry.symbol == normalized_symbol)
            .filter(IntradayMinuteCacheEntry.trade_date == trade_date)
            .filter(IntradayMinuteCacheEntry.timeframe == timeframe)
            .one_or_none()
        )
        if cache_entry is None:
            return IntradayCacheLookup(status="miss", items=[])

        cached_bars = (
            session.query(MinuteBar)
            .filter(MinuteBar.instrument_id == cache_entry.instrument_id)
            .filter(MinuteBar.ts >= cache_entry.first_ts)
            .filter(MinuteBar.ts <= cache_entry.last_ts)
            .order_by(MinuteBar.ts)
            .all()
        )
    except SQLAlchemyError:
        session.rollback()
        return IntradayCacheLookup(status="unavailable", items=[], reason=INTRADAY_CACHE_UNAVAILABLE_REASON)

    if len(cached_bars) < cache_entry.row_count:
        return IntradayCacheLookup(status="miss", items=[])

    return IntradayCacheLookup(
        status="hit",
        items=[serialize_cached_intraday_bar(bar) for bar in cached_bars],
        entry=cache_entry,
    )


def _persist_intraday_cache_bars(
    *,
    symbol: str,
    trade_date: date,
    timeframe: str,
    session: Session | None,
    provider_name: str,
    session_status: str,
    bars: list[ProviderIntradayBar],
    cache_lookup_status: str,
) -> IntradayCacheWriteResult:
    fetched_at = datetime.now(timezone.utc)
    fetched_at_iso = fetched_at.isoformat()
    if session_status != "closed_session":
        return IntradayCacheWriteResult(status="skipped", fetched_at=fetched_at_iso, cached_at=None)
    if session is None or cache_lookup_status == "unavailable" or not _can_use_persistent_intraday_cache(provider_name, symbol):
        return IntradayCacheWriteResult(
            status="unavailable",
            fetched_at=fetched_at_iso,
            cached_at=None,
            reason=INTRADAY_CACHE_UNAVAILABLE_REASON,
        )
    if not bars:
        return IntradayCacheWriteResult(status="miss", fetched_at=fetched_at_iso, cached_at=None)

    normalized_bars = [(bar, _normalize_intraday_timestamp(bar.timestamp)) for bar in bars]
    first_ts = min(timestamp for _, timestamp in normalized_bars)
    last_ts = max(timestamp for _, timestamp in normalized_bars)
    cached_at = datetime.now(timezone.utc)
    normalized_symbol = _normalize_intraday_cache_symbol(symbol)

    try:
        instrument = _get_or_create_intraday_cache_instrument(
            session=session,
            provider_name=provider_name,
            symbol=normalized_symbol,
        )
        for provider_bar, timestamp in normalized_bars:
            minute_bar = session.get(MinuteBar, (instrument.id, timestamp))
            if minute_bar is None:
                minute_bar = MinuteBar(instrument_id=instrument.id, ts=timestamp)
                session.add(minute_bar)
            minute_bar.open = provider_bar.open
            minute_bar.high = provider_bar.high
            minute_bar.low = provider_bar.low
            minute_bar.close = provider_bar.close
            minute_bar.volume = Decimal(provider_bar.volume)
            minute_bar.amount = provider_bar.amount

        cache_entry = (
            session.query(IntradayMinuteCacheEntry)
            .filter(IntradayMinuteCacheEntry.provider == provider_name)
            .filter(IntradayMinuteCacheEntry.symbol == normalized_symbol)
            .filter(IntradayMinuteCacheEntry.trade_date == trade_date)
            .filter(IntradayMinuteCacheEntry.timeframe == timeframe)
            .one_or_none()
        )
        if cache_entry is None:
            cache_entry = IntradayMinuteCacheEntry(
                provider=provider_name,
                symbol=normalized_symbol,
                trade_date=trade_date,
                timeframe=timeframe,
            )
            session.add(cache_entry)
        cache_entry.instrument_id = instrument.id
        cache_entry.source = INTRADAY_CACHE_SOURCE
        cache_entry.row_count = len(normalized_bars)
        cache_entry.first_ts = first_ts
        cache_entry.last_ts = last_ts
        cache_entry.fetched_at = fetched_at
        cache_entry.cached_at = cached_at
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        return IntradayCacheWriteResult(
            status="unavailable",
            fetched_at=fetched_at_iso,
            cached_at=None,
            reason=INTRADAY_CACHE_UNAVAILABLE_REASON,
        )

    return IntradayCacheWriteResult(status="stored", fetched_at=fetched_at_iso, cached_at=cached_at.isoformat())


def _can_use_persistent_intraday_cache(provider_name: str, symbol: str) -> bool:
    return _infer_intraday_market(provider_name, symbol) in INTRADAY_MARKET_META


def _get_or_create_intraday_cache_instrument(
    *,
    session: Session,
    provider_name: str,
    symbol: str,
) -> Instrument:
    market_code = _infer_intraday_market(provider_name, symbol)
    if market_code is None:
        msg = f"Cannot infer intraday cache market for provider={provider_name} symbol={symbol}"
        raise ValueError(msg)

    market = session.query(Market).filter(Market.code == market_code).one_or_none()
    if market is None:
        market_meta = INTRADAY_MARKET_META[market_code]
        market = Market(
            code=market_code,
            name=market_meta["name"],
            timezone=market_meta["timezone"],
            currency=market_meta["currency"],
        )
        session.add(market)
        session.flush()

    instrument = (
        session.query(Instrument)
        .filter(Instrument.market_id == market.id)
        .filter(Instrument.symbol == symbol)
        .one_or_none()
    )
    if instrument is not None:
        return instrument

    instrument = Instrument(
        symbol=symbol,
        name=symbol,
        market=market,
        asset_type="stock",
        currency=market.currency,
    )
    session.add(instrument)
    session.flush()
    return instrument


def _provider_intraday_cache_status(cache_lookup_status: str, cache_write_status: str, session_status: str) -> str:
    if session_status != "closed_session":
        return "skipped"
    if cache_lookup_status == "unavailable" or cache_write_status == "unavailable":
        return "unavailable"
    return "miss"


def _provider_empty_intraday_cache_status(cache_lookup_status: str, session_status: str) -> str:
    if session_status != "closed_session":
        return "skipped"
    if cache_lookup_status == "unavailable":
        return "unavailable"
    return "miss"


def _normalize_intraday_cache_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def _normalize_intraday_timestamp(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _intraday_freshness_status_for_reason(reason: str) -> str:
    if reason == INTRADAY_UNSUPPORTED_REASON:
        return "unsupported"
    if reason in {
        INTRADAY_FUTURE_NO_DATA_REASON,
        INTRADAY_WEEKEND_NO_DATA_REASON,
        INTRADAY_KNOWN_HOLIDAY_NO_DATA_REASON,
        INTRADAY_NO_DATA_REASON,
    }:
        return "no_data"
    return "unknown"


def _intraday_cache_status_for_reason(reason: str) -> str:
    if reason in {
        INTRADAY_FUTURE_NO_DATA_REASON,
        INTRADAY_WEEKEND_NO_DATA_REASON,
        INTRADAY_KNOWN_HOLIDAY_NO_DATA_REASON,
        INTRADAY_UNSUPPORTED_REASON,
    }:
        return "skipped"
    return "miss"


def _classify_regular_intraday_session_status(trade_date: date) -> str:
    if trade_date == date.today():
        return "current_session"
    return "closed_session"


def _intraday_session_status_for_reason(reason: str, trade_date: date) -> str:
    if reason == INTRADAY_FUTURE_NO_DATA_REASON:
        return "future_date"
    if reason == INTRADAY_WEEKEND_NO_DATA_REASON:
        return "weekend"
    if reason == INTRADAY_KNOWN_HOLIDAY_NO_DATA_REASON:
        return "known_holiday"
    if reason == INTRADAY_UNSUPPORTED_REASON:
        return "unsupported_market"
    if reason == INTRADAY_NO_DATA_REASON:
        return _classify_regular_intraday_session_status(trade_date)
    return "unknown"


def _infer_intraday_market(provider_name: str, symbol: str) -> str | None:
    if provider_name == "yfinance" and _symbol_looks_like_us_equity(symbol):
        return "US"
    return None


def _infer_intraday_timezone(provider_name: str, symbol: str) -> str | None:
    if provider_name == "yfinance" and _symbol_looks_like_us_equity(symbol):
        return "America/New_York"
    return None


def _get_previous_close_reference(
    *,
    symbol: str,
    trade_date: date,
    session: Session | None,
    provider_name: str,
) -> float | None:
    lookback_start = trade_date - timedelta(days=INTRADAY_PREVIOUS_CLOSE_LOOKBACK_DAYS)
    lookback_end = trade_date - timedelta(days=1)
    if lookback_end < lookback_start:
        return None

    try:
        bars_payload = get_bars_payload(
            symbol,
            "1d",
            lookback_start,
            lookback_end,
            session=session,
            provider_name=provider_name,
        )
    except (MarketDataProviderError, ValueError, SQLAlchemyError):
        return None

    items = bars_payload.get("items")
    if not isinstance(items, list) or not items:
        return None

    latest_item = items[-1]
    if not isinstance(latest_item, dict):
        return None

    close_value = latest_item.get("close")
    if isinstance(close_value, int | float):
        return float(close_value)
    return None


def _get_previous_close_reference_from_database(
    *,
    symbol: str,
    trade_date: date,
    session: Session | None,
) -> float | None:
    if session is None:
        return None

    lookback_start = trade_date - timedelta(days=INTRADAY_PREVIOUS_CLOSE_LOOKBACK_DAYS)
    lookback_end = trade_date - timedelta(days=1)
    if lookback_end < lookback_start:
        return None

    try:
        db_bars = _fetch_daily_bars_from_database(symbol, lookback_start, lookback_end, session)
    except SQLAlchemyError:
        session.rollback()
        return None

    if not db_bars:
        return None
    return float(db_bars[-1].close)


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
    capabilities = {
        "order_book": bool(provider_capabilities["order_book"]),
        "recent_trades": bool(provider_capabilities["recent_trades"]),
        "large_orders": bool(provider_capabilities["large_orders"]),
        "fund_flow": bool(provider_capabilities["fund_flow"]),
    }

    provider = get_provider(effective_provider_name)
    if not _provider_supports_verified_market_depth(provider):
        return _build_unsupported_market_depth_payload(
            symbol=symbol,
            requested_provider_name=requested_provider_name,
            effective_provider_name=effective_provider_name,
            depth_levels=depth_levels,
            threshold_amount=threshold_amount,
            provider_capabilities=capabilities,
            provider_reason=str(provider_capabilities["reason"]),
        )

    snapshot = _fetch_provider_market_depth(provider, effective_provider_name, symbol, depth_levels)
    if snapshot is None:
        return _build_unsupported_market_depth_payload(
            symbol=symbol,
            requested_provider_name=requested_provider_name,
            effective_provider_name=effective_provider_name,
            depth_levels=depth_levels,
            threshold_amount=threshold_amount,
            provider_capabilities=capabilities,
            provider_reason=str(provider_capabilities["reason"]),
        )

    return _build_provider_market_depth_payload(
        symbol=symbol,
        requested_provider_name=requested_provider_name,
        effective_provider_name=effective_provider_name,
        depth_levels=depth_levels,
        threshold_amount=threshold_amount,
        snapshot=snapshot,
    )


def _build_unsupported_market_depth_payload(
    *,
    symbol: str,
    requested_provider_name: str | None,
    effective_provider_name: str,
    depth_levels: int,
    threshold_amount: Decimal,
    provider_capabilities: dict[str, bool],
    provider_reason: str,
) -> dict[str, object]:

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
            "capabilities": provider_capabilities,
        },
    }


def _build_provider_market_depth_payload(
    *,
    symbol: str,
    requested_provider_name: str | None,
    effective_provider_name: str,
    depth_levels: int,
    threshold_amount: Decimal,
    snapshot: ProviderMarketDepthSnapshot,
) -> dict[str, object]:
    serialized_snapshot = _serialize_provider_market_depth_snapshot(snapshot, effective_provider_name)
    bids = list(serialized_snapshot["bids"])
    asks = list(serialized_snapshot["asks"])
    recent_trades = list(serialized_snapshot["recent_trades"])
    fund_flow = serialized_snapshot["fund_flow"]
    large_orders = _derive_large_orders_from_recent_trades(recent_trades, threshold_amount)
    has_order_book = bool(bids or asks)
    has_recent_trades = bool(recent_trades)
    has_large_orders = bool(large_orders)
    has_fund_flow = _fund_flow_has_values(fund_flow)
    has_any_verified_section = has_order_book or has_recent_trades or has_large_orders or has_fund_flow
    capabilities = {
        "order_book": has_order_book,
        "recent_trades": has_recent_trades,
        "large_orders": has_large_orders,
        "fund_flow": has_fund_flow,
    }
    partial_reason = snapshot.availability.get("reason") if isinstance(snapshot.availability, dict) else None
    availability_reason = str(partial_reason) if partial_reason else None
    as_of = snapshot.as_of.isoformat() if snapshot.as_of is not None else None

    return {
        "symbol": symbol,
        "source": snapshot.source,
        "provider": snapshot.provider or effective_provider_name,
        "requested_provider": requested_provider_name,
        "effective_provider": effective_provider_name,
        "status": "ok" if has_any_verified_section else "degraded",
        "as_of": as_of,
        "is_realtime": snapshot.is_realtime,
        "is_delayed": snapshot.is_delayed,
        "delay_minutes": snapshot.delay_minutes,
        "order_book": {
            "status": "ok" if has_order_book else "degraded",
            "reason": None if has_order_book else MARKET_DEPTH_UNSUPPORTED_REASON,
            "as_of": as_of,
            "depth_levels": depth_levels,
            "bids": bids[:depth_levels],
            "asks": asks[:depth_levels],
        },
        "recent_trades": {
            "status": "ok" if has_recent_trades else "degraded",
            "reason": None if has_recent_trades else RECENT_TRADES_UNSUPPORTED_REASON,
            "as_of": as_of,
            "items": recent_trades,
        },
        "large_orders": {
            "status": "ok" if has_large_orders else "degraded",
            "reason": None if has_large_orders else LARGE_ORDERS_UNSUPPORTED_REASON,
            "threshold_amount": float(threshold_amount),
            "threshold_volume": None,
            "currency": _fund_flow_currency(fund_flow),
            "as_of": as_of,
            "items": large_orders,
        },
        "fund_flow": {
            "status": "ok" if has_fund_flow else "degraded",
            "reason": None if has_fund_flow else FUND_FLOW_UNSUPPORTED_REASON,
            "as_of": as_of,
            **fund_flow,
        },
        "availability": {
            "status": "ok" if has_any_verified_section else "degraded",
            "reason": availability_reason,
            "capabilities": capabilities,
        },
    }


def _derive_large_orders_from_recent_trades(
    recent_trades: list[object],
    threshold_amount: Decimal,
) -> list[dict[str, object]]:
    large_orders: list[dict[str, object]] = []
    for trade in recent_trades:
        if not isinstance(trade, dict):
            continue
        amount = trade.get("amount")
        if not isinstance(amount, int | float):
            continue
        if Decimal(str(amount)) >= threshold_amount:
            large_orders.append({**trade, "threshold_amount": float(threshold_amount), "threshold_volume": None})
    return large_orders


def _fund_flow_has_values(fund_flow: object) -> bool:
    if not isinstance(fund_flow, dict):
        return False
    return any(
        fund_flow.get(field_name) is not None
        for field_name in ("net_inflow", "main_net_inflow", "retail_net_inflow")
    )


def _fund_flow_currency(fund_flow: object) -> str | None:
    if not isinstance(fund_flow, dict):
        return None
    currency = fund_flow.get("currency")
    return currency if isinstance(currency, str) else None


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
