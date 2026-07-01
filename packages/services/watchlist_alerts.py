from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from packages.services.alerts import evaluate_alert_rules
from packages.services.alert_triggers import record_triggered_alerts
from packages.services.indicators import get_stored_indicators_payload
from packages.services.market_data import get_latest_bars_batch_payload
from packages.shared.config import settings


def _has_alert_rules(item: dict[str, object]) -> bool:
    rules = item.get("alert_rules")
    if not isinstance(rules, dict):
        return False
    return any(rules.get(key) is not None for key in ("price_above", "rsi_below"))


def evaluate_all_watchlist_alerts(
    session: Session,
    provider_name: str | None = None,
) -> dict[str, object]:
    from packages.services.watchlists import get_active_watchlist_item_dicts

    provider = provider_name or settings.market_data_provider
    items = [item for item in get_active_watchlist_item_dicts(session) if _has_alert_rules(item)]
    if not items:
        return {
            "status": "skipped",
            "reason": "no_alert_rules",
            "item_count": 0,
            "triggered_count": 0,
            "items": [],
        }

    enriched = enrich_watchlist_items(items, session=session, provider_name=provider)
    triggered_count = sum(
        1
        for item in enriched
        if isinstance(item.get("alert_status"), dict) and item["alert_status"].get("triggered")
    )
    return {
        "status": "evaluated",
        "provider": provider,
        "item_count": len(enriched),
        "triggered_count": triggered_count,
        "items": [
            {
                "symbol": item["symbol"],
                "market": item["market"],
                "alert_status": item.get("alert_status"),
            }
            for item in enriched
        ],
    }


def enrich_watchlist_items(
    items: list[dict[str, object]],
    session: Session,
    provider_name: str | None = None,
) -> list[dict[str, object]]:
    if not items:
        return []

    provider = provider_name or settings.market_data_provider
    symbols = [str(item["symbol"]) for item in items]
    price_map: dict[str, float | None] = {}
    try:
        latest_payload = get_latest_bars_batch_payload(
            symbols,
            session=session,
            provider_name=provider,
        )
        for entry in latest_payload["items"]:
            item = entry.get("item")
            price_map[str(entry["symbol"])] = float(item["close"]) if item else None
    except Exception:
        price_map = {symbol: None for symbol in symbols}

    enriched: list[dict[str, object]] = []
    for item in items:
        symbol = str(item["symbol"])
        price = price_map.get(symbol)
        rsi: float | None = None
        try:
            indicators_payload = get_stored_indicators_payload(symbol, session=session)
            rsi_value = indicators_payload.get("indicators", {}).get("rsi")
            if rsi_value is not None:
                rsi = float(rsi_value)
        except (SQLAlchemyError, KeyError, TypeError, ValueError):
            rsi = None

        alert_status = evaluate_alert_rules(item.get("alert_rules"), price, rsi)
        record_triggered_alerts(
            symbol,
            str(item["market"]),
            alert_status,
            session=session,
        )

        enriched.append(
            {
                **item,
                "latest_price": price,
                "rsi": rsi,
                "alert_status": alert_status,
            }
        )
    return enriched
