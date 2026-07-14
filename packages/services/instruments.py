from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from packages.domain.models import Instrument, Market
from packages.providers.mock_provider import MockProvider

DEFAULT_MARKETS = ("CN", "HK", "US")
MAX_INSTRUMENT_PAGE_SIZE = 100


def _serialize_database_instrument(instrument: Instrument) -> dict[str, str]:
    market = instrument.market.code if instrument.market is not None else ""
    exchange = instrument.exchange.code if instrument.exchange is not None else ""
    return {
        "symbol": instrument.symbol,
        "name": instrument.name,
        "market": market,
        "exchange": exchange,
        "asset_type": instrument.asset_type,
        "currency": instrument.currency,
        "source": "database",
    }


def _seed_instruments() -> list[dict[str, str]]:
    provider = MockProvider()
    instruments = []
    for market in DEFAULT_MARKETS:
        for instrument in provider.fetch_instruments(market):
            instruments.append(
                {
                    "symbol": instrument.symbol,
                    "name": instrument.name,
                    "market": instrument.market,
                    "exchange": instrument.exchange,
                    "asset_type": instrument.asset_type,
                    "currency": instrument.currency,
                    "source": "seed",
                }
            )
    return instruments


def _matches_filters(item: dict[str, str], query: str | None, market: str | None) -> bool:
    if market and item["market"].upper() != market.upper():
        return False
    if not query:
        return True
    normalized_query = query.strip().lower()
    return normalized_query in item["symbol"].lower() or normalized_query in item["name"].lower()


def _validate_pagination(limit: int | None, offset: int) -> None:
    if limit is not None and not 1 <= limit <= MAX_INSTRUMENT_PAGE_SIZE:
        raise ValueError(
            f"Instrument limit must be between 1 and {MAX_INSTRUMENT_PAGE_SIZE}."
        )
    if offset < 0:
        raise ValueError("Instrument offset cannot be negative.")


def _paginate_items(
    items: list[dict[str, str]],
    *,
    limit: int | None,
    offset: int,
) -> list[dict[str, str]]:
    if limit is None:
        return items[offset:]
    return items[offset : offset + limit]


def _build_instruments_payload(
    *,
    source: str,
    items: list[dict[str, str]],
    total: int,
    limit: int | None,
    offset: int,
) -> dict[str, object]:
    return {
        "source": source,
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(items) < total,
    }


def list_instruments_payload(
    session: Session | None = None,
    query: str | None = None,
    market: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> dict[str, object]:
    _validate_pagination(limit, offset)

    if session is not None:
        try:
            database_query = (
                session.query(Instrument)
                .outerjoin(Market, Instrument.market_id == Market.id)
                .filter(Instrument.is_active.is_(True))
            )

            if database_query.count() > 0:
                normalized_query = query.strip() if query else ""
                if normalized_query:
                    database_query = database_query.filter(
                        or_(
                            Instrument.symbol.icontains(
                                normalized_query,
                                autoescape=True,
                            ),
                            Instrument.name.icontains(
                                normalized_query,
                                autoescape=True,
                            ),
                        )
                    )
                if market:
                    database_query = database_query.filter(
                        Market.code.ilike(market.strip())
                    )

                total = database_query.count()
                page_query = database_query.order_by(
                    Market.code.asc(), Instrument.symbol.asc()
                ).offset(offset)
                if limit is not None:
                    page_query = page_query.limit(limit)
                instruments = page_query.all()
                items = [
                    _serialize_database_instrument(instrument)
                    for instrument in instruments
                ]
                return _build_instruments_payload(
                    source="database",
                    items=items,
                    total=total,
                    limit=limit,
                    offset=offset,
                )
        except SQLAlchemyError:
            session.rollback()

    filtered_items = [
        item for item in _seed_instruments() if _matches_filters(item, query, market)
    ]
    total = len(filtered_items)
    return _build_instruments_payload(
        source="seed",
        items=_paginate_items(filtered_items, limit=limit, offset=offset),
        total=total,
        limit=limit,
        offset=offset,
    )
