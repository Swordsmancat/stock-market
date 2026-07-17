from __future__ import annotations

from collections import Counter
from decimal import Decimal
from typing import Literal

from sqlalchemy import func
from sqlalchemy.orm import Session, aliased

from packages.domain.models import DailyBar, Exchange, Instrument, Market


SUPPORTED_MARKET = "CN"
SUPPORTED_DIRECTIONS = {"gainers", "losers"}
SUPPORTED_EXCHANGES = {"all", "SSE", "SZSE", "BSE"}
SUPPORTED_LIMITS = {10, 20, 50}

MarketMoverDirection = Literal["gainers", "losers"]


def _validate_request(
    *, market: str, direction: str, exchange: str, limit: int
) -> tuple[str, str, str, int]:
    normalized_market = market.strip().upper()
    normalized_direction = direction.strip().lower()
    normalized_exchange = exchange.strip().upper()
    if normalized_exchange == "ALL":
        normalized_exchange = "all"

    if normalized_market != SUPPORTED_MARKET:
        raise ValueError(f"Unsupported market: {market}")
    if normalized_direction not in SUPPORTED_DIRECTIONS:
        raise ValueError(f"Unsupported market-mover direction: {direction}")
    if normalized_exchange not in SUPPORTED_EXCHANGES:
        raise ValueError(f"Unsupported exchange: {exchange}")
    if limit not in SUPPORTED_LIMITS:
        raise ValueError("Market-mover limit must be 10, 20, or 50.")
    return normalized_market, normalized_direction, normalized_exchange, limit


def _empty_payload(
    *,
    market: str,
    direction: str,
    exchange: str,
    limit: int,
    trade_date: str | None = None,
    previous_trade_date: str | None = None,
    provider: str | None = None,
    adjustment: str | None = None,
    omitted_count: int = 0,
) -> dict[str, object]:
    return {
        "status": "no_data",
        "market": market,
        "direction": direction,
        "exchange": exchange,
        "limit": limit,
        "trade_date": trade_date,
        "previous_trade_date": previous_trade_date,
        "provider": provider,
        "adjustment": adjustment,
        "sources": [],
        "comparable_count": 0,
        "eligible_count": 0,
        "omitted_count": omitted_count,
        "count": 0,
        "items": [],
        "data_mode": "stored",
        "research_signal_only": True,
    }


def _finite_decimal(value: Decimal | None) -> Decimal | None:
    if value is None or not value.is_finite():
        return None
    return value


def get_market_movers_payload(
    *,
    session: Session,
    market: str = SUPPORTED_MARKET,
    direction: str = "gainers",
    exchange: str = "all",
    limit: int = 20,
) -> dict[str, object]:
    market, direction, exchange, limit = _validate_request(
        market=market,
        direction=direction,
        exchange=exchange,
        limit=limit,
    )

    trade_dates = (
        session.query(DailyBar.trade_date)
        .join(Instrument, DailyBar.instrument_id == Instrument.id)
        .join(Market, Instrument.market_id == Market.id)
        .filter(Market.code == market)
        .filter(Instrument.asset_type == "stock")
        .filter(Instrument.is_active.is_(True))
        .distinct()
        .order_by(DailyBar.trade_date.desc())
        .limit(2)
        .all()
    )
    if len(trade_dates) < 2:
        return _empty_payload(
            market=market,
            direction=direction,
            exchange=exchange,
            limit=limit,
        )

    trade_date = trade_dates[0][0]
    previous_trade_date = trade_dates[1][0]
    cohort_current = aliased(DailyBar, name="market_mover_cohort_current")
    cohort_previous = aliased(DailyBar, name="market_mover_cohort_previous")
    cohort = (
        session.query(
            cohort_current.provider,
            cohort_current.adjustment,
            func.count(cohort_current.instrument_id).label("instrument_count"),
        )
        .join(Instrument, cohort_current.instrument_id == Instrument.id)
        .join(Market, Instrument.market_id == Market.id)
        .join(
            cohort_previous,
            (cohort_previous.instrument_id == cohort_current.instrument_id)
            & (cohort_previous.trade_date == previous_trade_date)
            & (cohort_previous.provider == cohort_current.provider)
            & (cohort_previous.adjustment == cohort_current.adjustment),
        )
        .filter(Market.code == market)
        .filter(Instrument.asset_type == "stock")
        .filter(Instrument.is_active.is_(True))
        .filter(cohort_current.trade_date == trade_date)
        .group_by(cohort_current.provider, cohort_current.adjustment)
        .order_by(
            func.count(cohort_current.instrument_id).desc(),
            cohort_current.provider.asc(),
            cohort_current.adjustment.asc(),
        )
        .first()
    )
    if cohort is None:
        return _empty_payload(
            market=market,
            direction=direction,
            exchange=exchange,
            limit=limit,
            trade_date=trade_date.isoformat(),
            previous_trade_date=previous_trade_date.isoformat(),
        )

    provider, adjustment, _coherent_cohort_count = cohort
    scope_count_query = (
        session.query(func.count(DailyBar.instrument_id))
        .join(Instrument, DailyBar.instrument_id == Instrument.id)
        .join(Market, Instrument.market_id == Market.id)
        .join(Exchange, Instrument.exchange_id == Exchange.id)
        .filter(Market.code == market)
        .filter(Instrument.asset_type == "stock")
        .filter(Instrument.is_active.is_(True))
        .filter(DailyBar.trade_date == trade_date)
        .filter(DailyBar.provider == provider)
        .filter(DailyBar.adjustment == adjustment)
    )
    if exchange != "all":
        scope_count_query = scope_count_query.filter(Exchange.code == exchange)
    scope_cohort_count = int(scope_count_query.scalar() or 0)
    current_bar = aliased(DailyBar, name="market_mover_current")
    previous_bar = aliased(DailyBar, name="market_mover_previous")
    query = (
        session.query(Instrument, Exchange.code, current_bar, previous_bar)
        .join(Market, Instrument.market_id == Market.id)
        .join(Exchange, Instrument.exchange_id == Exchange.id)
        .join(
            current_bar,
            (current_bar.instrument_id == Instrument.id)
            & (current_bar.trade_date == trade_date),
        )
        .join(
            previous_bar,
            (previous_bar.instrument_id == Instrument.id)
            & (previous_bar.trade_date == previous_trade_date),
        )
        .filter(Market.code == market)
        .filter(Instrument.asset_type == "stock")
        .filter(Instrument.is_active.is_(True))
        .filter(current_bar.provider == provider)
        .filter(current_bar.adjustment == adjustment)
        .filter(previous_bar.provider == provider)
        .filter(previous_bar.adjustment == adjustment)
    )
    if exchange != "all":
        query = query.filter(Exchange.code == exchange)

    rows = query.all()
    comparable_items: list[dict[str, object]] = []
    sources: Counter[str] = Counter()
    invalid_count = 0
    for instrument, exchange_code, current, previous in rows:
        close = _finite_decimal(current.close)
        previous_close = _finite_decimal(previous.close)
        volume = _finite_decimal(current.volume)
        amount = _finite_decimal(current.amount)
        if (
            close is None
            or previous_close is None
            or previous_close <= 0
            or volume is None
        ):
            invalid_count += 1
            continue
        change = close - previous_close
        change_percent = change / previous_close * Decimal("100")
        if not change_percent.is_finite():
            invalid_count += 1
            continue
        sources[current.source] += 1
        comparable_items.append(
            {
                "symbol": instrument.symbol,
                "name": instrument.name,
                "exchange": exchange_code,
                "close": float(close),
                "previous_close": float(previous_close),
                "change": float(change),
                "change_percent": float(change_percent),
                "volume": float(volume),
                "amount": float(amount) if amount is not None else None,
                "provider": current.provider,
                "source": current.source,
                "adjustment": current.adjustment,
            }
        )

    directional_items = [
        item
        for item in comparable_items
        if (
            item["change_percent"] > 0
            if direction == "gainers"
            else item["change_percent"] < 0
        )
    ]
    if direction == "gainers":
        directional_items.sort(
            key=lambda item: (
                -item["change_percent"],
                -item["change"],
                item["symbol"],
            )
        )
    else:
        directional_items.sort(
            key=lambda item: (
                item["change_percent"],
                item["change"],
                item["symbol"],
            )
        )

    selected_items = directional_items[:limit]
    for rank, item in enumerate(selected_items, start=1):
        item["rank"] = rank

    omitted_count = max(scope_cohort_count - len(rows), 0) + invalid_count
    return {
        "status": "ok" if selected_items else "no_data",
        "market": market,
        "direction": direction,
        "exchange": exchange,
        "limit": limit,
        "trade_date": trade_date.isoformat(),
        "previous_trade_date": previous_trade_date.isoformat(),
        "provider": provider,
        "adjustment": adjustment,
        "sources": [
            {"source": source, "instrument_count": count}
            for source, count in sorted(sources.items())
        ],
        "comparable_count": len(comparable_items),
        "eligible_count": len(directional_items),
        "omitted_count": omitted_count,
        "count": len(selected_items),
        "items": selected_items,
        "data_mode": "stored",
        "research_signal_only": True,
    }
