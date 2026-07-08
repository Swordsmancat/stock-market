"""API router for InStock-inspired strategy screening research signals."""

from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from packages.services import market_data as market_data_service
from packages.services.market_data import MarketDataProviderError
from packages.services.strategy_screening import (
    DISCLAIMER,
    screen_latest_instock_strategies,
)
from packages.shared.database import get_session

router = APIRouter(prefix="/strategies", tags=["strategies"])

MAX_STRATEGY_SYMBOLS = 12
DEFAULT_STRATEGY_LOOKBACK_DAYS = 365


def _parse_symbol_list(symbols: str) -> list[str]:
    parsed_symbols: list[str] = []
    seen_symbols: set[str] = set()
    for raw_symbol in symbols.split(","):
        normalized_symbol = raw_symbol.strip().upper()
        if not normalized_symbol or normalized_symbol in seen_symbols:
            continue
        parsed_symbols.append(normalized_symbol)
        seen_symbols.add(normalized_symbol)
    return parsed_symbols[:MAX_STRATEGY_SYMBOLS]


def _parse_csv_values(value: str | None) -> list[str] | None:
    if value is None:
        return None
    values = [item.strip() for item in value.split(",") if item.strip()]
    return values or None


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@router.get("/screen")
def screen_strategies(
    symbols: str = Query(..., description="Comma-separated symbols to screen"),
    strategies: str | None = Query(
        default=None,
        description="Comma-separated strategy codes to evaluate",
    ),
    start: date | None = Query(default=None, description="Historical lookback start date"),
    end: date | None = Query(default=None, description="Historical lookback end date"),
    limit: int = Query(20, ge=1, le=50, description="Maximum flattened matches to return"),
    provider: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    symbol_list = _parse_symbol_list(symbols)
    if not symbol_list:
        raise HTTPException(status_code=400, detail="At least one symbol is required")

    effective_end = end or date.today()
    effective_start = start or (effective_end - timedelta(days=DEFAULT_STRATEGY_LOOKBACK_DAYS))
    if effective_start > effective_end:
        raise HTTPException(status_code=400, detail="start must be on or before end")

    requested_strategies = _parse_csv_values(strategies)
    symbol_payloads: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    matches: list[dict[str, Any]] = []

    for symbol in symbol_list:
        try:
            bars_payload = market_data_service.get_bars_payload(
                symbol,
                "1d",
                effective_start,
                effective_end,
                session=session,
                provider_name=provider,
            )
        except MarketDataProviderError as error:
            diagnostics.append(
                {
                    "symbol": symbol,
                    "status": "provider_error",
                    "category": error.category,
                    "provider": error.provider_name,
                }
            )
            continue
        except ValueError as error:
            diagnostics.append(
                {
                    "symbol": symbol,
                    "status": "invalid_request",
                    "message": str(error),
                }
            )
            continue

        symbol_payload = screen_latest_instock_strategies(
            symbol,
            bars_payload.get("items", []),
            strategy_codes=requested_strategies,
        )
        symbol_payload.update(
            {
                "source": bars_payload.get("source"),
                "provider": bars_payload.get("provider"),
                "requested_provider": bars_payload.get("requested_provider"),
                "effective_provider": bars_payload.get("effective_provider"),
            }
        )
        symbol_payloads.append(symbol_payload)
        matches.extend(symbol_payload["matches"])

    ranked_matches = sorted(
        matches,
        key=lambda match: float(match.get("confidence", 0.0)),
        reverse=True,
    )[:limit]

    return {
        "status": "ok",
        "generated_at": _utc_timestamp(),
        "start": effective_start.isoformat(),
        "end": effective_end.isoformat(),
        "count": len(ranked_matches),
        "items": ranked_matches,
        "symbols": symbol_payloads,
        "diagnostics": diagnostics,
        "research_signal_only": True,
        "disclaimer": DISCLAIMER,
    }
