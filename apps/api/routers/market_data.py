from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from packages.services.market_data import get_bars_payload, get_indicator_payload
from packages.shared.database import get_session

router = APIRouter(prefix="/market-data", tags=["market-data"])


@router.get("/{symbol}/bars")
def get_bars(
    symbol: str,
    timeframe: str = Query(default="1d"),
    start: date = Query(...),
    end: date = Query(...),
    session: Session = Depends(get_session),
) -> dict:
    return get_bars_payload(symbol, timeframe, start, end, session=session)


@router.get("/{symbol}/indicators")
def get_indicators(
    symbol: str,
    start: date = Query(...),
    end: date = Query(...),
    ma_window: int = Query(default=20, ge=1),
    session: Session = Depends(get_session),
) -> dict:
    return get_indicator_payload(symbol, start, end, ma_window, session=session)
