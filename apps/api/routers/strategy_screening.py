"""API router for InStock-inspired strategy screening research signals."""

from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from packages.services import market_data as market_data_service
from packages.services.market_data import MarketDataProviderError
from packages.services.strategy_screening import (
    DISCLAIMER,
    evaluate_instock_strategy_signals,
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


def _parse_forward_windows(value: str | None) -> list[int] | None:
    raw_values = _parse_csv_values(value)
    if raw_values is None:
        return None

    windows: list[int] = []
    for raw_value in raw_values:
        try:
            windows.append(int(raw_value))
        except ValueError as parse_error:
            raise HTTPException(
                status_code=400,
                detail="forward_windows must be comma-separated integers",
            ) from parse_error
    return windows


def _normalize_required_symbol(symbol: str) -> str:
    normalized_symbol = symbol.strip().upper()
    if not normalized_symbol:
        raise HTTPException(status_code=400, detail="Symbol is required")
    return normalized_symbol


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _fetch_strategy_bars(
    *,
    symbol: str,
    start: date,
    end: date,
    session: Session,
    provider: str | None,
) -> tuple[dict[str, object], list[dict[str, Any]]]:
    bars_payload = market_data_service.get_bars_payload(
        symbol,
        "1d",
        start,
        end,
        session=session,
        provider_name=provider,
    )
    items = bars_payload.get("items")
    return bars_payload, items if isinstance(items, list) else []


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
            bars_payload, bars = _fetch_strategy_bars(
                symbol=symbol,
                start=effective_start,
                end=effective_end,
                session=session,
                provider=provider,
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
            bars,
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


@router.get("/evaluate")
def evaluate_strategies(
    symbol: str = Query(..., description="Symbol to evaluate"),
    start: date = Query(..., description="Historical evaluation start date"),
    end: date = Query(..., description="Historical evaluation end date"),
    strategies: str | None = Query(
        default=None,
        description="Comma-separated strategy codes to evaluate",
    ),
    forward_windows: str | None = Query(
        default=None,
        description="Comma-separated forward-return windows in trading bars",
    ),
    benchmark_symbol: str | None = Query(
        default=None,
        description="Optional benchmark symbol for relative returns",
    ),
    provider: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    if start > end:
        raise HTTPException(status_code=400, detail="start must be on or before end")

    normalized_symbol = _normalize_required_symbol(symbol)
    requested_strategies = _parse_csv_values(strategies)
    requested_forward_windows = _parse_forward_windows(forward_windows)
    try:
        bars_payload, bars = _fetch_strategy_bars(
            symbol=normalized_symbol,
            start=start,
            end=end,
            session=session,
            provider=provider,
        )
    except MarketDataProviderError as error:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Market data provider unavailable for strategy evaluation.",
                "provider": error.provider_name,
                "category": error.category,
            },
        ) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    normalized_benchmark_symbol = (
        _normalize_required_symbol(benchmark_symbol) if benchmark_symbol else None
    )
    benchmark_bars = None
    if normalized_benchmark_symbol is not None:
        try:
            _, benchmark_bars = _fetch_strategy_bars(
                symbol=normalized_benchmark_symbol,
                start=start,
                end=end,
                session=session,
                provider=provider,
            )
        except MarketDataProviderError as error:
            raise HTTPException(
                status_code=502,
                detail={
                    "message": "Market data provider unavailable for strategy benchmark evaluation.",
                    "provider": error.provider_name,
                    "category": error.category,
                },
            ) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    payload = evaluate_instock_strategy_signals(
        normalized_symbol,
        bars,
        strategy_codes=requested_strategies,
        forward_windows=requested_forward_windows,
        benchmark_bars=benchmark_bars,
    )
    return {
        **payload,
        "generated_at": _utc_timestamp(),
        "source": bars_payload.get("source"),
        "provider": bars_payload.get("provider"),
        "requested_provider": bars_payload.get("requested_provider"),
        "effective_provider": bars_payload.get("effective_provider"),
        "benchmark_symbol": normalized_benchmark_symbol,
        "research_signal_only": True,
    }
