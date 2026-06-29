from datetime import date

from fastapi import APIRouter, Query

from packages.services.market_data import get_bars_payload, get_indicator_payload

router = APIRouter(prefix="/market-data", tags=["market-data"])


@router.get("/{symbol}/bars")
def get_bars(
    symbol: str,
    timeframe: str = Query(default="1d"),
    start: date = Query(...),
    end: date = Query(...),
) -> dict:
    return get_bars_payload(symbol, timeframe, start, end)


@router.get("/{symbol}/indicators")
def get_indicators(
    symbol: str,
    start: date = Query(...),
    end: date = Query(...),
    ma_window: int = Query(default=20, ge=1),
) -> dict:
    return get_indicator_payload(symbol, start, end, ma_window)
