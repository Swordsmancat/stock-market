from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from packages.services.analysis import refresh_stock_analysis
from packages.shared.database import get_session

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/refresh")
def refresh_analysis(
    symbol: str = Query(...),
    market: str = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    ma_window: int = Query(default=20, ge=1),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return refresh_stock_analysis(
        symbol=symbol,
        market=market,
        start=start,
        end=end,
        session=session,
        ma_window=ma_window,
    )
