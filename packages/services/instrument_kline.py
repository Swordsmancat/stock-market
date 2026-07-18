from __future__ import annotations

from collections import Counter
from datetime import timedelta
from decimal import Decimal

from sqlalchemy import and_, case, func, or_
from sqlalchemy.orm import Session, aliased

from packages.domain.models import DailyBar, Exchange, Instrument, Market
from packages.services.stored_daily_bars import choose_daily_bar_cohort_key


SUPPORTED_ASSET_TYPES = ("stock", "etf", "index")
SUPPORTED_PERIODS = {"1m": 31, "3m": 93, "6m": 186, "1y": 366}
MAX_CATALOG_LIMIT = 50


def _normalize_request(
    *,
    query: str | None,
    asset_type: str | None,
    symbol: str | None,
    market: str | None,
    period: str,
    limit: int,
    offset: int,
) -> tuple[str | None, str | None, str | None, str | None, str, int, int]:
    normalized_query = query.strip() if query else None
    if normalized_query and len(normalized_query) > 64:
        raise ValueError("K-line search query must be at most 64 characters.")

    normalized_asset_type = asset_type.strip().lower() if asset_type else None
    if normalized_asset_type and normalized_asset_type not in SUPPORTED_ASSET_TYPES:
        raise ValueError(f"Unsupported K-line asset type: {asset_type}")

    normalized_symbol = symbol.strip().upper() if symbol else None
    normalized_market = market.strip().upper() if market else None
    if bool(normalized_symbol) != bool(normalized_market):
        raise ValueError("K-line symbol and market must be supplied together.")
    if normalized_symbol and len(normalized_symbol) > 64:
        raise ValueError("K-line symbol must be at most 64 characters.")
    if normalized_market and len(normalized_market) > 16:
        raise ValueError("K-line market must be at most 16 characters.")

    normalized_period = period.strip().lower()
    if normalized_period not in SUPPORTED_PERIODS:
        raise ValueError(f"Unsupported K-line period: {period}")
    if not 1 <= limit <= MAX_CATALOG_LIMIT:
        raise ValueError("K-line catalog limit must be between 1 and 50.")
    if offset < 0:
        raise ValueError("K-line catalog offset cannot be negative.")

    return (
        normalized_query,
        normalized_asset_type,
        normalized_symbol,
        normalized_market,
        normalized_period,
        limit,
        offset,
    )


def _finite_decimal(value: Decimal | None) -> Decimal | None:
    if value is None or not value.is_finite():
        return None
    return value


def _serialize_catalog_row(row: tuple[object, ...]) -> dict[str, object]:
    (
        instrument,
        market_code,
        exchange_code,
        latest_date,
        bar_count,
        latest_close,
        latest_provider,
        latest_source,
        latest_adjustment,
    ) = row
    close = _finite_decimal(latest_close)
    latest_bar = None
    if latest_date is not None:
        latest_bar = {
            "timestamp": latest_date.isoformat(),
            "close": float(close) if close is not None and close > 0 else None,
            "provider": latest_provider or None,
            "source": latest_source or None,
            "adjustment": latest_adjustment or None,
        }
    return {
        "id": f"{market_code}-{instrument.symbol}",
        "symbol": instrument.symbol,
        "name": instrument.name,
        "market": market_code,
        "exchange": exchange_code,
        "asset_type": instrument.asset_type,
        "currency": instrument.currency,
        "stored_bar_count": int(bar_count or 0),
        "has_series": bool(bar_count),
        "latest_bar": latest_bar,
    }


def _catalog_query(
    *,
    session: Session,
    query: str | None,
    asset_type: str | None,
):
    latest_summary = (
        session.query(
            DailyBar.instrument_id.label("instrument_id"),
            func.max(DailyBar.trade_date).label("latest_date"),
            func.count(DailyBar.trade_date).label("bar_count"),
        )
        .group_by(DailyBar.instrument_id)
        .subquery()
    )
    latest_bar = aliased(DailyBar)
    catalog_query = (
        session.query(
            Instrument,
            Market.code,
            Exchange.code,
            latest_summary.c.latest_date,
            latest_summary.c.bar_count,
            latest_bar.close,
            latest_bar.provider,
            latest_bar.source,
            latest_bar.adjustment,
        )
        .join(Market, Instrument.market_id == Market.id)
        .outerjoin(Exchange, Instrument.exchange_id == Exchange.id)
        .outerjoin(
            latest_summary,
            latest_summary.c.instrument_id == Instrument.id,
        )
        .outerjoin(
            latest_bar,
            and_(
                latest_bar.instrument_id == Instrument.id,
                latest_bar.trade_date == latest_summary.c.latest_date,
            ),
        )
        .filter(Instrument.is_active.is_(True))
        .filter(Instrument.asset_type.in_(SUPPORTED_ASSET_TYPES))
    )
    if query:
        catalog_query = catalog_query.filter(
            or_(
                Instrument.symbol.icontains(query, autoescape=True),
                Instrument.name.icontains(query, autoescape=True),
            )
        )
    if asset_type:
        catalog_query = catalog_query.filter(Instrument.asset_type == asset_type)
    return catalog_query


def _selected_identity(
    *,
    session: Session,
    symbol: str,
    market: str,
    asset_type: str | None,
) -> tuple[Instrument, str, str | None] | None:
    query = (
        session.query(Instrument, Market.code, Exchange.code)
        .join(Market, Instrument.market_id == Market.id)
        .outerjoin(Exchange, Instrument.exchange_id == Exchange.id)
        .filter(Instrument.is_active.is_(True))
        .filter(Instrument.asset_type.in_(SUPPORTED_ASSET_TYPES))
        .filter(Instrument.symbol == symbol)
        .filter(Market.code == market)
    )
    if asset_type is not None:
        return query.filter(Instrument.asset_type == asset_type).one_or_none()
    return query.order_by(
        case(
            (Instrument.asset_type == "stock", 0),
            (Instrument.asset_type == "etf", 1),
            else_=2,
        )
    ).first()


def _serialize_identity(
    instrument: Instrument,
    market_code: str,
    exchange_code: str | None,
) -> dict[str, object]:
    return {
        "id": f"{market_code}-{instrument.symbol}",
        "symbol": instrument.symbol,
        "name": instrument.name,
        "market": market_code,
        "exchange": exchange_code,
        "asset_type": instrument.asset_type,
        "currency": instrument.currency,
    }


def _serialize_series(
    *,
    session: Session,
    instrument: Instrument,
    period: str,
) -> tuple[dict[str, object] | None, list[str]]:
    cohort_counts = (
        session.query(
            DailyBar.provider,
            DailyBar.adjustment,
            func.count(DailyBar.trade_date),
        )
        .filter(DailyBar.instrument_id == instrument.id)
        .group_by(DailyBar.provider, DailyBar.adjustment)
        .all()
    )
    cohort_key = choose_daily_bar_cohort_key(cohort_counts)
    if cohort_key is None:
        return None, ["NO_STORED_DAILY_BARS"]

    provider, adjustment = cohort_key
    anchor_date = (
        session.query(func.max(DailyBar.trade_date))
        .filter(DailyBar.instrument_id == instrument.id)
        .filter(DailyBar.provider == provider)
        .filter(DailyBar.adjustment == adjustment)
        .scalar()
    )
    if anchor_date is None:
        return None, ["NO_STORED_DAILY_BARS"]

    period_start = anchor_date - timedelta(days=SUPPORTED_PERIODS[period])
    rows = (
        session.query(DailyBar)
        .filter(DailyBar.instrument_id == instrument.id)
        .filter(DailyBar.provider == provider)
        .filter(DailyBar.adjustment == adjustment)
        .filter(DailyBar.trade_date >= period_start)
        .filter(DailyBar.trade_date <= anchor_date)
        .order_by(DailyBar.trade_date.asc())
        .all()
    )

    items: list[dict[str, object]] = []
    dropped_count = 0
    source_counts: Counter[str] = Counter()
    for row in rows:
        open_value = _finite_decimal(row.open)
        high_value = _finite_decimal(row.high)
        low_value = _finite_decimal(row.low)
        close_value = _finite_decimal(row.close)
        volume_value = _finite_decimal(row.volume)
        if (
            open_value is None
            or high_value is None
            or low_value is None
            or close_value is None
            or volume_value is None
            or min(open_value, high_value, low_value, close_value) <= 0
            or volume_value < 0
            or high_value < low_value
        ):
            dropped_count += 1
            continue
        source_counts[row.source or "unknown"] += 1
        items.append(
            {
                "timestamp": row.trade_date.isoformat(),
                "open": float(open_value),
                "high": float(high_value),
                "low": float(low_value),
                "close": float(close_value),
                "volume": float(volume_value),
            }
        )

    diagnostics = ["INVALID_STORED_BARS_DROPPED"] if dropped_count else []
    if not items:
        diagnostics.append("NO_VALID_STORED_DAILY_BARS")
        return None, diagnostics

    return (
        {
            "provider": provider or None,
            "adjustment": adjustment or None,
            "anchor_date": anchor_date.isoformat(),
            "period_start": period_start.isoformat(),
            "first_date": items[0]["timestamp"],
            "last_date": items[-1]["timestamp"],
            "bar_count": len(items),
            "sources": [
                {"source": source, "bar_count": count}
                for source, count in sorted(source_counts.items())
            ],
            "items": items,
        },
        diagnostics,
    )


def get_instrument_kline_payload(
    *,
    session: Session,
    query: str | None = None,
    asset_type: str | None = None,
    symbol: str | None = None,
    market: str | None = None,
    period: str = "3m",
    limit: int = 20,
    offset: int = 0,
) -> dict[str, object]:
    (
        query,
        asset_type,
        symbol,
        market,
        period,
        limit,
        offset,
    ) = _normalize_request(
        query=query,
        asset_type=asset_type,
        symbol=symbol,
        market=market,
        period=period,
        limit=limit,
        offset=offset,
    )

    catalog_query = _catalog_query(
        session=session,
        query=query,
        asset_type=asset_type,
    )
    total = catalog_query.count()
    catalog_rows = (
        catalog_query.order_by(
            Market.code.asc(),
            Instrument.asset_type.asc(),
            Instrument.symbol.asc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    catalog = [_serialize_catalog_row(row) for row in catalog_rows]

    base_payload: dict[str, object] = {
        "source": "database",
        "query": {
            "q": query,
            "asset_type": asset_type,
            "symbol": symbol,
            "market": market,
            "period": period,
            "limit": limit,
            "offset": offset,
        },
        "catalog": catalog,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(catalog) < total,
        "data_mode": "stored",
        "research_signal_only": True,
        "safety": {
            "no_provider_request": True,
            "no_automated_trading": True,
        },
    }
    if symbol is None or market is None:
        return {
            **base_payload,
            "status": "empty",
            "selected": None,
            "series": None,
            "diagnostics": [],
        }

    selected_row = _selected_identity(
        session=session,
        symbol=symbol,
        market=market,
        asset_type=asset_type,
    )
    if selected_row is None:
        return {
            **base_payload,
            "status": "not_found",
            "selected": None,
            "series": None,
            "diagnostics": ["SELECTED_INSTRUMENT_NOT_FOUND"],
        }

    instrument, market_code, exchange_code = selected_row
    selected = _serialize_identity(instrument, market_code, exchange_code)
    series, diagnostics = _serialize_series(
        session=session,
        instrument=instrument,
        period=period,
    )
    return {
        **base_payload,
        "status": "ready" if series is not None else "no_data",
        "selected": selected,
        "series": series,
        "diagnostics": diagnostics,
    }
