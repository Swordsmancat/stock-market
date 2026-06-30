from sqlalchemy.orm import Session

from packages.domain.models import Watchlist, WatchlistItem
from packages.shared.config import settings

DEFAULT_WATCHLIST_NAME = "default"
_DEFAULT_NAMES = {
    "600519": "Kweichow Moutai",
    "0700": "Tencent Holdings",
    "AAPL": "Apple Inc.",
}


def _parse_watchlist_config(watchlist: str) -> list[dict[str, str]]:
    items = []
    for entry in watchlist.split(","):
        value = entry.strip()
        if not value:
            continue
        symbol, market = value.split(":", 1)
        normalized_symbol = symbol.strip().upper()
        items.append(
            {
                "symbol": normalized_symbol,
                "market": market.strip().upper(),
                "name": _DEFAULT_NAMES.get(normalized_symbol, normalized_symbol),
            }
        )
    return items


def _get_or_create_default_watchlist(session: Session) -> Watchlist:
    watchlist = session.query(Watchlist).filter(Watchlist.name == DEFAULT_WATCHLIST_NAME).first()
    if watchlist is None:
        watchlist = Watchlist(name=DEFAULT_WATCHLIST_NAME, is_default=True)
        session.add(watchlist)
        session.flush()
    return watchlist


def _serialize_item(item: WatchlistItem) -> dict[str, object]:
    return {
        "symbol": item.symbol,
        "market": item.market,
        "name": item.name,
        "is_active": item.is_active,
        "alert_rules": item.alert_rules,
    }


def _active_items(watchlist: Watchlist, session: Session) -> list[WatchlistItem]:
    return (
        session.query(WatchlistItem)
        .filter(WatchlistItem.watchlist_id == watchlist.id)
        .filter(WatchlistItem.is_active.is_(True))
        .order_by(WatchlistItem.created_at.asc(), WatchlistItem.symbol.asc())
        .all()
    )


def _seed_default_items_if_empty(watchlist: Watchlist, session: Session) -> None:
    if _active_items(watchlist, session):
        return

    for item in _parse_watchlist_config(settings.daily_report_watchlist):
        session.add(
            WatchlistItem(
                watchlist_id=watchlist.id,
                symbol=item["symbol"],
                market=item["market"],
                name=item["name"],
                is_active=True,
                alert_rules={},
            )
        )
    session.commit()


def get_default_watchlist_payload(session: Session) -> dict[str, object]:
    watchlist = _get_or_create_default_watchlist(session)
    _seed_default_items_if_empty(watchlist, session)
    items = _active_items(watchlist, session)
    return {
        "name": watchlist.name,
        "source": "database",
        "items": [_serialize_item(item) for item in items],
    }


def upsert_watchlist_item(
    symbol: str,
    market: str,
    session: Session,
    name: str | None = None,
    alert_rules: dict[str, object] | None = None,
    is_active: bool = True,
) -> dict[str, object]:
    watchlist = _get_or_create_default_watchlist(session)
    normalized_symbol = symbol.upper()
    normalized_market = market.upper()
    item = (
        session.query(WatchlistItem)
        .filter(WatchlistItem.watchlist_id == watchlist.id)
        .filter(WatchlistItem.symbol == normalized_symbol)
        .filter(WatchlistItem.market == normalized_market)
        .first()
    )
    values = {
        "symbol": normalized_symbol,
        "market": normalized_market,
        "name": name or _DEFAULT_NAMES.get(normalized_symbol, normalized_symbol),
        "is_active": is_active,
        "alert_rules": alert_rules or {},
    }
    if item is None:
        item = WatchlistItem(watchlist_id=watchlist.id, **values)
        session.add(item)
    else:
        for key, value in values.items():
            setattr(item, key, value)
    session.commit()

    return {"source": "database", "item": _serialize_item(item)}


def get_active_watchlist_entries(session: Session) -> list[tuple[str, str]]:
    payload = get_default_watchlist_payload(session)
    return [(str(item["symbol"]), str(item["market"])) for item in payload["items"]]


def format_watchlist_entries(entries: list[tuple[str, str]]) -> str:
    return ",".join(f"{symbol}:{market}" for symbol, market in entries)
