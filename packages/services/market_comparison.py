from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta
from decimal import Decimal
from typing import Sequence

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from packages.domain.models import DailyBar, Exchange, Instrument, Market


SUPPORTED_MARKET = "CN"
SUPPORTED_PERIODS = {"1m": 31, "3m": 93, "6m": 186, "1y": 366}
MAX_SELECTED_SYMBOLS = 4
MAX_SEARCH_LIMIT = 12


def _finite_decimal(value: Decimal | None) -> Decimal | None:
    if value is None or not value.is_finite():
        return None
    return value


def _normalize_request(
    *,
    market: str,
    symbols: Sequence[str],
    period: str,
    query: str | None,
    search_limit: int,
) -> tuple[str, tuple[str, ...], str, str | None, int]:
    normalized_market = market.strip().upper()
    if normalized_market != SUPPORTED_MARKET:
        raise ValueError(f"Unsupported comparison market: {market}")

    normalized_period = period.strip().lower()
    if normalized_period not in SUPPORTED_PERIODS:
        raise ValueError(f"Unsupported comparison period: {period}")

    normalized_symbols: list[str] = []
    seen: set[str] = set()
    for symbol in symbols:
        normalized = symbol.strip().upper()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        normalized_symbols.append(normalized)
    if len(normalized_symbols) > MAX_SELECTED_SYMBOLS:
        raise ValueError("Select at most four comparison symbols.")

    normalized_query = query.strip() if query else None
    if normalized_query and len(normalized_query) > 64:
        raise ValueError("Comparison search query must be at most 64 characters.")
    if not 1 <= search_limit <= MAX_SEARCH_LIMIT:
        raise ValueError("Comparison search limit must be between 1 and 12.")

    return (
        normalized_market,
        tuple(normalized_symbols),
        normalized_period,
        normalized_query,
        search_limit,
    )


def _serialize_instrument(
    instrument: Instrument,
    *,
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
    }


def _search_stored_instruments(
    *,
    session: Session,
    market: str,
    query: str | None,
    selected_symbols: tuple[str, ...],
    limit: int,
) -> list[dict[str, object]]:
    if not query:
        return []

    rows_query = (
        session.query(Instrument, Market.code, Exchange.code)
        .join(Market, Instrument.market_id == Market.id)
        .outerjoin(Exchange, Instrument.exchange_id == Exchange.id)
        .filter(Market.code == market)
        .filter(Instrument.asset_type == "stock")
        .filter(Instrument.is_active.is_(True))
        .filter(
            or_(
                Instrument.symbol.icontains(query, autoescape=True),
                Instrument.name.icontains(query, autoescape=True),
            )
        )
    )
    if selected_symbols:
        rows_query = rows_query.filter(Instrument.symbol.notin_(selected_symbols))
    rows = rows_query.order_by(Instrument.symbol.asc()).limit(limit).all()
    return [
        _serialize_instrument(
            instrument,
            market_code=market_code,
            exchange_code=exchange_code,
        )
        for instrument, market_code, exchange_code in rows
    ]


def _choose_coherent_series(rows: list[DailyBar]) -> tuple[list[DailyBar], str, str] | None:
    cohorts: dict[tuple[str, str], list[DailyBar]] = defaultdict(list)
    for row in rows:
        cohorts[(row.provider or "", row.adjustment or "")].append(row)
    if not cohorts:
        return None

    (provider, adjustment), chosen_rows = sorted(
        cohorts.items(),
        key=lambda item: (-len(item[1]), item[0][0], item[0][1]),
    )[0]
    finite_rows = [
        row
        for row in chosen_rows
        if (close := _finite_decimal(row.close)) is not None and close > 0
    ]
    finite_rows.sort(key=lambda row: row.trade_date)
    return finite_rows, provider, adjustment


def get_market_comparison_payload(
    *,
    session: Session,
    market: str = SUPPORTED_MARKET,
    symbols: Sequence[str] = (),
    period: str = "3m",
    query: str | None = None,
    search_limit: int = 8,
) -> dict[str, object]:
    market, symbols, period, query, search_limit = _normalize_request(
        market=market,
        symbols=symbols,
        period=period,
        query=query,
        search_limit=search_limit,
    )
    search_results = _search_stored_instruments(
        session=session,
        market=market,
        query=query,
        selected_symbols=symbols,
        limit=search_limit,
    )

    base_payload: dict[str, object] = {
        "market": market,
        "symbols": list(symbols),
        "period": period,
        "requested_count": len(symbols),
        "search_results": search_results,
        "data_mode": "stored",
        "research_signal_only": True,
        "safety": {
            "no_provider_request": True,
            "no_automated_trading": True,
        },
    }
    if not symbols:
        return {
            **base_payload,
            "status": "empty_selection",
            "anchor_date": None,
            "period_start": None,
            "shared_dates": [],
            "shared_date_count": 0,
            "comparable_count": 0,
            "missing_symbols": [],
            "diagnostics": [],
            "items": [],
        }

    instrument_rows = (
        session.query(Instrument, Market.code, Exchange.code)
        .join(Market, Instrument.market_id == Market.id)
        .outerjoin(Exchange, Instrument.exchange_id == Exchange.id)
        .filter(Market.code == market)
        .filter(Instrument.asset_type == "stock")
        .filter(Instrument.is_active.is_(True))
        .filter(Instrument.symbol.in_(symbols))
        .all()
    )
    instruments_by_symbol = {
        instrument.symbol: (instrument, market_code, exchange_code)
        for instrument, market_code, exchange_code in instrument_rows
    }
    missing_symbols = [symbol for symbol in symbols if symbol not in instruments_by_symbol]
    ordered_instruments = [
        instruments_by_symbol[symbol]
        for symbol in symbols
        if symbol in instruments_by_symbol
    ]
    instrument_ids = [instrument.id for instrument, _, _ in ordered_instruments]

    anchor_date = None
    if instrument_ids:
        anchor_date = (
            session.query(func.max(DailyBar.trade_date))
            .filter(DailyBar.instrument_id.in_(instrument_ids))
            .scalar()
        )
    period_start = (
        anchor_date - timedelta(days=SUPPORTED_PERIODS[period])
        if anchor_date is not None
        else None
    )
    bars_by_instrument: dict[object, list[DailyBar]] = defaultdict(list)
    if anchor_date is not None and period_start is not None:
        bar_rows = (
            session.query(DailyBar)
            .filter(DailyBar.instrument_id.in_(instrument_ids))
            .filter(DailyBar.trade_date >= period_start)
            .filter(DailyBar.trade_date <= anchor_date)
            .order_by(DailyBar.instrument_id.asc(), DailyBar.trade_date.asc())
            .all()
        )
        for bar in bar_rows:
            bars_by_instrument[bar.instrument_id].append(bar)

    items: list[dict[str, object]] = []
    comparable_date_sets: list[set[str]] = []
    provenance_pairs: set[tuple[str, str]] = set()
    for instrument, market_code, exchange_code in ordered_instruments:
        identity = _serialize_instrument(
            instrument,
            market_code=market_code,
            exchange_code=exchange_code,
        )
        chosen = _choose_coherent_series(bars_by_instrument[instrument.id])
        if chosen is None:
            items.append(
                {
                    **identity,
                    "status": "no_data",
                    "provider": None,
                    "adjustment": None,
                    "sources": [],
                    "first_date": None,
                    "last_date": None,
                    "bar_count": 0,
                    "bars": [],
                }
            )
            continue

        coherent_rows, provider, adjustment = chosen
        serialized_bars = [
            {
                "timestamp": row.trade_date.isoformat(),
                "close": float(row.close),
            }
            for row in coherent_rows
        ]
        date_set = {str(bar["timestamp"]) for bar in serialized_bars}
        if serialized_bars:
            comparable_date_sets.append(date_set)
            provenance_pairs.add((provider, adjustment))
        source_counts = Counter(row.source or "unknown" for row in coherent_rows)
        items.append(
            {
                **identity,
                "status": "ok" if serialized_bars else "no_data",
                "provider": provider or None,
                "adjustment": adjustment or None,
                "sources": [
                    {"source": source, "bar_count": count}
                    for source, count in sorted(source_counts.items())
                ],
                "first_date": serialized_bars[0]["timestamp"] if serialized_bars else None,
                "last_date": serialized_bars[-1]["timestamp"] if serialized_bars else None,
                "bar_count": len(serialized_bars),
                "bars": serialized_bars,
            }
        )

    shared_dates = (
        sorted(set.intersection(*comparable_date_sets))
        if comparable_date_sets
        else []
    )
    shared_date_set = set(shared_dates)
    for item in items:
        if item["status"] != "ok":
            continue
        item["bars"] = [
            bar for bar in item["bars"] if bar["timestamp"] in shared_date_set
        ]
        item["bar_count"] = len(item["bars"])
        item["first_date"] = shared_dates[0] if shared_dates else None
        item["last_date"] = shared_dates[-1] if shared_dates else None

    comparable_count = sum(1 for item in items if item["status"] == "ok")
    diagnostics: list[str] = []
    if missing_symbols:
        diagnostics.append("MISSING_REQUESTED_SYMBOLS")
    if len(provenance_pairs) > 1:
        diagnostics.append("MIXED_SERIES_PROVENANCE")
    if len(symbols) >= 2 and (comparable_count < 2 or len(shared_dates) < 2):
        diagnostics.append("INSUFFICIENT_SHARED_DATES")

    if len(symbols) < 2:
        status = "insufficient_selection"
    elif comparable_count < 2 or len(shared_dates) < 2:
        status = "no_data"
    else:
        status = "ok"

    return {
        **base_payload,
        "status": status,
        "anchor_date": anchor_date.isoformat() if anchor_date is not None else None,
        "period_start": period_start.isoformat() if period_start is not None else None,
        "shared_dates": shared_dates,
        "shared_date_count": len(shared_dates),
        "comparable_count": comparable_count,
        "missing_symbols": missing_symbols,
        "diagnostics": diagnostics,
        "items": items,
    }
