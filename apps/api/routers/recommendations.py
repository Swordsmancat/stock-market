"""API router for smart recommendations."""

from datetime import date, datetime, timedelta, timezone
from typing import Any
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from packages.services import market_data as market_data_service
from packages.services.market_data import MarketDataProviderError
from packages.services.smart_recommendations import (
    RecommendationEngine,
    calculate_indicators,
    evaluate_recommendation_signals,
)
from packages.shared.database import get_session

logger = logging.getLogger(__name__)
router = APIRouter()

MAX_RECOMMENDATION_SYMBOLS = 12
RECOMMENDATION_LOOKBACK_DAYS = 180


def _parse_symbol_list(symbols: str) -> list[str]:
    parsed_symbols: list[str] = []
    seen_symbols: set[str] = set()

    for raw_symbol in symbols.split(","):
        normalized_symbol = raw_symbol.strip().upper()
        if not normalized_symbol or normalized_symbol in seen_symbols:
            continue
        parsed_symbols.append(normalized_symbol)
        seen_symbols.add(normalized_symbol)

    return parsed_symbols[:MAX_RECOMMENDATION_SYMBOLS]


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


def _read_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _build_recommendation_bars(items: object) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []

    bars: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        timestamp = item.get("timestamp")
        close = _read_float(item.get("close"))
        if not isinstance(timestamp, str) or close is None:
            continue

        normalized_bar: dict[str, Any] = {
            "timestamp": timestamp,
            "close": close,
        }
        for price_field in ("open", "high", "low"):
            price_value = _read_float(item.get(price_field))
            if price_value is not None:
                normalized_bar[price_field] = price_value
        volume = _read_float(item.get("volume"))
        if volume is not None:
            normalized_bar["volume"] = volume
        bars.append(normalized_bar)

    return bars


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _fetch_recommendation_bars(
    *,
    symbol: str,
    start: date,
    end: date,
    session: Session,
    provider: str | None,
) -> tuple[dict[str, object], list[dict[str, Any]]]:
    try:
        bars_payload = market_data_service.get_bars_payload(
            symbol,
            "1d",
            start,
            end,
            session=session,
            provider_name=provider,
        )
    except MarketDataProviderError as error:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Market data provider unavailable for recommendation evaluation.",
                "provider": error.provider_name,
                "category": error.category,
            },
        ) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return bars_payload, _build_recommendation_bars(bars_payload.get("items"))


@router.get("/recommendations/evaluate")
def evaluate_recommendations(
    symbol: str = Query(..., description="Symbol to evaluate"),
    start: date = Query(..., description="Historical evaluation start date"),
    end: date = Query(..., description="Historical evaluation end date"),
    signal_types: str | None = Query(
        default=None,
        description="Comma-separated signal types to evaluate",
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
    requested_signal_types = _parse_csv_values(signal_types)
    requested_forward_windows = _parse_forward_windows(forward_windows)
    bars_payload, bars = _fetch_recommendation_bars(
        symbol=normalized_symbol,
        start=start,
        end=end,
        session=session,
        provider=provider,
    )
    normalized_benchmark_symbol = (
        _normalize_required_symbol(benchmark_symbol) if benchmark_symbol else None
    )
    benchmark_bars = None
    if normalized_benchmark_symbol is not None:
        _, benchmark_bars = _fetch_recommendation_bars(
            symbol=normalized_benchmark_symbol,
            start=start,
            end=end,
            session=session,
            provider=provider,
        )

    payload = evaluate_recommendation_signals(
        normalized_symbol,
        bars,
        signal_types=requested_signal_types,
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


@router.get("/recommendations")
async def get_smart_recommendations(
    symbols: str = Query(..., description="Comma-separated list of symbols"),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of recommendations"),
    provider: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    """
    Get research signal candidates for given symbols.

    Analyzes technical patterns and returns unbacktested research candidates.
    """
    symbol_list = _parse_symbol_list(symbols)
    if not symbol_list:
        raise HTTPException(status_code=400, detail="At least one symbol is required")

    end_date = date.today()
    start_date = end_date - timedelta(days=RECOMMENDATION_LOOKBACK_DAYS)
    recommendation_engine = RecommendationEngine()
    recommendations: list[dict[str, Any]] = []
    diagnostics: list[dict[str, str]] = []

    for symbol in symbol_list:
        try:
            bars_payload = market_data_service.get_bars_payload(
                symbol,
                "1d",
                start_date,
                end_date,
                session=session,
                provider_name=provider,
            )
        except MarketDataProviderError as error:
            logger.warning("Recommendation source unavailable for %s: %s", symbol, error)
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

        bars = _build_recommendation_bars(bars_payload.get("items"))
        if not bars:
            diagnostics.append(
                {
                    "symbol": symbol,
                    "status": "no_data",
                }
            )
            continue

        indicators = calculate_indicators(bars)
        recommendations.extend(
            recommendation_engine.generate_recommendations(symbol, bars, indicators)
        )

    ranked_recommendations = sorted(
        recommendations,
        key=lambda recommendation: float(recommendation.get("confidence", 0)),
        reverse=True,
    )[:limit]

    return {
        "status": "ok",
        "generated_at": _utc_timestamp(),
        "count": len(ranked_recommendations),
        "items": ranked_recommendations,
        "diagnostics": diagnostics,
        "research_signal_only": True,
        "disclaimer": "Technical signal candidates are not investment advice.",
    }
