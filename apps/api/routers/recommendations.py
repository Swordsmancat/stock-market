"""API router for smart recommendations."""

from datetime import date, datetime, timedelta, timezone
from typing import Any
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from packages.services import market_data as market_data_service
from packages.services.market_data import MarketDataProviderError
from packages.services.smart_recommendations import RecommendationEngine, calculate_indicators
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
        volume = _read_float(item.get("volume"))
        if volume is not None:
            normalized_bar["volume"] = volume
        bars.append(normalized_bar)

    return bars


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


@router.get("/recommendations")
async def get_smart_recommendations(
    symbols: str = Query(..., description="Comma-separated list of symbols"),
    limit: int = Query(5, ge=1, le=20, description="Maximum number of recommendations"),
    provider: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    """
    Get smart recommendations for given symbols.
    
    Analyzes technical patterns and returns actionable recommendations.
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
    }
