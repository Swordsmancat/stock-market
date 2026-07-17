from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from packages.services.market_movers import get_market_movers_payload
from packages.shared.database import get_session


router = APIRouter(prefix="/market-movers", tags=["market-movers"])


@router.get("")
def get_market_movers(
    market: Literal["CN"] = Query("CN"),
    direction: Literal["gainers", "losers"] = Query("gainers"),
    exchange: Literal["all", "SSE", "SZSE", "BSE"] = Query("all"),
    limit: int = Query(20, ge=10, le=50),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    if limit not in {10, 20, 50}:
        raise HTTPException(status_code=422, detail="Limit must be 10, 20, or 50.")
    return get_market_movers_payload(
        session=session,
        market=market,
        direction=direction,
        exchange=exchange,
        limit=limit,
    )
