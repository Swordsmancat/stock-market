from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from packages.domain.models import Instrument, Market
from packages.providers.mock_provider import MockProvider

DEFAULT_MARKETS = ("CN", "HK", "US")


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


def list_instruments_payload(
    session: Session | None = None,
    query: str | None = None,
    market: str | None = None,
) -> dict[str, object]:
    items: list[dict[str, str]] = []
    source = "seed"

    if session is not None:
        try:
            instruments = (
                session.query(Instrument)
                .outerjoin(Market, Instrument.market_id == Market.id)
                .filter(Instrument.is_active.is_(True))
                .order_by(Market.code.asc(), Instrument.symbol.asc())
                .all()
            )
            items = [_serialize_database_instrument(instrument) for instrument in instruments]
            if items:
                source = "database"
        except SQLAlchemyError:
            session.rollback()
            items = []

    if not items:
        items = _seed_instruments()

    filtered_items = [item for item in items if _matches_filters(item, query, market)]
    return {"source": source, "items": filtered_items}
