from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from packages.services.instrument_kline import get_instrument_kline_payload
from packages.shared.database import get_session


router = APIRouter(prefix="/instrument-kline", tags=["instrument-kline"])


@router.get("")
def get_instrument_kline(
    q: str | None = Query(default=None, max_length=64),
    asset_type: Literal["stock", "etf", "index"] | None = Query(default=None),
    symbol: str | None = Query(default=None, max_length=64),
    market: str | None = Query(default=None, max_length=16),
    period: Literal["1m", "3m", "6m", "1y"] = Query(default="3m"),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        return get_instrument_kline_payload(
            session=session,
            query=q,
            asset_type=asset_type,
            symbol=symbol,
            market=market,
            period=period,
            limit=limit,
            offset=offset,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
