from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from packages.services.instruments import list_instruments_payload
from packages.services.market_data import (
    MarketDataProviderError,
    get_bars_payload,
    resolve_market_data_provider_name,
)
from packages.services.market_indices import DEFAULT_MARKET_INDICES, MarketIndexDefinition, resolve_provider_symbol
from packages.services.market_indicators import get_buffett_indicator_payloads
from packages.services.watchlists import get_active_watchlist_item_dicts
from packages.shared.cache import cache_market_overview


FOLLOWED_INSTRUMENT_LIMIT = 6
DASHBOARD_RANGE_DAYS = 92
MILLISECONDS_PER_DAY = 24 * 60 * 60 * 1000


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _classify_freshness(timestamp: str | None, today: date) -> str:
    parsed_date = _parse_date(timestamp)
    if parsed_date is None:
        return "unavailable"
    days_since_latest_bar = (today - parsed_date).days
    return "fresh" if days_since_latest_bar <= 3 else "stale"


def _derive_daily_movement(items: list[dict[str, Any]]) -> dict[str, object] | None:
    if len(items) < 2:
        return None

    latest_item = items[-1]
    previous_item = items[-2]
    latest_close = float(latest_item["close"])
    previous_close = float(previous_item["close"])
    absolute_change = latest_close - previous_close
    percent_change = None if previous_close == 0 else absolute_change / previous_close
    direction = "up" if absolute_change > 0 else "down" if absolute_change < 0 else "flat"
    return {
        "direction": direction,
        "absolute_change": absolute_change,
        "percent_change": percent_change,
    }


def _build_latest_summary(items: list[dict[str, Any]]) -> dict[str, object] | None:
    if not items:
        return None

    latest_item = items[-1]
    return {
        "timestamp": latest_item.get("timestamp"),
        "close": latest_item.get("close"),
        "movement": _derive_daily_movement(items),
    }


def _build_bars_item(
    *,
    identity: dict[str, object],
    bars_payload: dict[str, object],
    today: date,
    detail_path: str | None = None,
) -> dict[str, object]:
    items = list(bars_payload.get("items", []))
    status = str(bars_payload.get("status") or ("ok" if items else "no_data"))
    latest = _build_latest_summary(items)
    freshness = "no_data" if status == "no_data" else _classify_freshness(str(latest["timestamp"]) if latest else None, today)
    return {
        **identity,
        "status": status,
        "freshness": freshness,
        "latest": latest,
        "bars": items,
        "source": bars_payload.get("source"),
        "provider": bars_payload.get("provider"),
        "requested_provider": bars_payload.get("requested_provider"),
        "effective_provider": bars_payload.get("effective_provider"),
        "detail_path": detail_path,
        "no_data_reason": bars_payload.get("no_data_reason"),
    }


def _build_unavailable_bars_item(
    *,
    identity: dict[str, object],
    provider_name: str,
    message: str,
    detail_path: str | None = None,
) -> dict[str, object]:
    return {
        **identity,
        "status": "unavailable",
        "freshness": "unavailable",
        "latest": None,
        "bars": [],
        "source": "unavailable",
        "provider": provider_name,
        "requested_provider": provider_name,
        "effective_provider": provider_name,
        "detail_path": detail_path,
        "no_data_reason": message,
    }


def _load_followed_instrument_candidates(session: Session) -> tuple[str, list[dict[str, object]]]:
    watchlist_items = get_active_watchlist_item_dicts(session=session)
    if watchlist_items:
        return "watchlist", watchlist_items[:FOLLOWED_INSTRUMENT_LIMIT]

    instruments_payload = list_instruments_payload(session=session)
    fallback_items = [
        {
            "symbol": item["symbol"],
            "name": item["name"],
            "market": item["market"],
            "currency": item.get("currency", ""),
        }
        for item in instruments_payload["items"][:FOLLOWED_INSTRUMENT_LIMIT]
    ]
    return "default_sample", fallback_items


def _serialize_followed_instruments(
    *,
    session: Session,
    provider_name: str,
    start: date,
    end: date,
    today: date,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    scope, candidates = _load_followed_instrument_candidates(session)
    diagnostics: list[dict[str, object]] = []
    items: list[dict[str, object]] = []

    for candidate in candidates:
        symbol = str(candidate["symbol"]).upper()
        market = str(candidate.get("market") or "")
        identity = {
            "symbol": symbol,
            "name": str(candidate.get("name") or symbol),
            "market": market,
            "currency": str(candidate.get("currency") or ""),
        }
        try:
            bars_payload = get_bars_payload(
                symbol,
                "1d",
                start,
                end,
                session=session,
                provider_name=provider_name,
            )
            items.append(
                _build_bars_item(
                    identity=identity,
                    bars_payload=bars_payload,
                    today=today,
                    detail_path=f"/instruments/{symbol}",
                )
            )
        except (MarketDataProviderError, ValueError) as error:
            diagnostics.append({"section": "followed", "symbol": symbol, "status": "unavailable", "message": str(error)})
            items.append(
                _build_unavailable_bars_item(
                    identity=identity,
                    provider_name=provider_name,
                    message=str(error),
                    detail_path=f"/instruments/{symbol}",
                )
            )

    return {"scope": scope, "limit": FOLLOWED_INSTRUMENT_LIMIT, "items": items}, diagnostics


def _serialize_market_index(
    *,
    index: MarketIndexDefinition,
    session: Session,
    provider_name: str,
    start: date,
    end: date,
    today: date,
) -> tuple[dict[str, object], dict[str, object] | None]:
    provider_symbol = resolve_provider_symbol(index, provider_name)
    identity = {
        "code": index.code,
        "name": index.name,
        "name_zh": index.name_zh,
        "region": index.region,
        "market": index.market,
        "currency": index.currency,
        "provider_symbol": provider_symbol,
    }
    try:
        bars_payload = get_bars_payload(
            provider_symbol,
            "1d",
            start,
            end,
            session=session,
            provider_name=provider_name,
        )
        return _build_bars_item(identity=identity, bars_payload=bars_payload, today=today), None
    except (MarketDataProviderError, ValueError) as error:
        diagnostic = {"section": "indices", "code": index.code, "status": "unavailable", "message": str(error)}
        return _build_unavailable_bars_item(identity=identity, provider_name=provider_name, message=str(error)), diagnostic


def _serialize_indices(
    *,
    session: Session,
    provider_name: str,
    start: date,
    end: date,
    today: date,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    items: list[dict[str, object]] = []
    diagnostics: list[dict[str, object]] = []
    for index in sorted(DEFAULT_MARKET_INDICES, key=lambda item: item.display_order):
        item, diagnostic = _serialize_market_index(
            index=index,
            session=session,
            provider_name=provider_name,
            start=start,
            end=end,
            today=today,
        )
        items.append(item)
        if diagnostic is not None:
            diagnostics.append(diagnostic)
    return {"items": items}, diagnostics


@cache_market_overview(ttl=300)
def get_market_overview_payload(
    *,
    session: Session,
    provider_name: str | None = None,
    today: date | None = None,
) -> dict[str, object]:
    resolved_today = today or date.today()
    start = resolved_today - timedelta(days=DASHBOARD_RANGE_DAYS)
    effective_provider_name = resolve_market_data_provider_name(provider_name)

    followed_payload, followed_diagnostics = _serialize_followed_instruments(
        session=session,
        provider_name=effective_provider_name,
        start=start,
        end=resolved_today,
        today=resolved_today,
    )
    indices_payload, index_diagnostics = _serialize_indices(
        session=session,
        provider_name=effective_provider_name,
        start=start,
        end=resolved_today,
        today=resolved_today,
    )
    valuation_items = get_buffett_indicator_payloads(session=session)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider": effective_provider_name,
        "range": {
            "timeframe": "1d",
            "start": start.isoformat(),
            "end": resolved_today.isoformat(),
        },
        "followed": followed_payload,
        "indices": indices_payload,
        "valuation_indicators": {"items": valuation_items},
        "diagnostics": [*followed_diagnostics, *index_diagnostics],
    }
