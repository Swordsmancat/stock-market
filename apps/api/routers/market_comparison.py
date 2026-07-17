from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from packages.services.market_comparison import get_market_comparison_payload
from packages.shared.database import get_session


router = APIRouter(prefix="/market-comparison", tags=["market-comparison"])


@router.get("")
def get_market_comparison(
    market: Literal["CN"] = Query("CN"),
    symbols: str = Query("", max_length=128),
    period: Literal["1m", "3m", "6m", "1y"] = Query("3m"),
    q: str | None = Query(default=None, max_length=64),
    search_limit: int = Query(default=8, ge=1, le=12),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        return get_market_comparison_payload(
            session=session,
            market=market,
            symbols=tuple(symbols.split(",")),
            period=period,
            query=q,
            search_limit=search_limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
