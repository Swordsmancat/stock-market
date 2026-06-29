from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from packages.services.indicators import (
    calculate_and_store_daily_indicators,
    get_stored_indicators_payload,
)
from packages.shared.database import get_session

router = APIRouter(prefix="/indicators", tags=["indicators"])


@router.post("/recalculate")
def recalculate_indicators(
    symbol: str = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    ma_window: int = Query(default=20, ge=1),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return calculate_and_store_daily_indicators(
        symbol,
        start,
        end,
        session=session,
        ma_window=ma_window,
    )


@router.get("/{symbol}")
def get_indicators(symbol: str, session: Session = Depends(get_session)) -> dict[str, object]:
    return get_stored_indicators_payload(symbol, session=session)
