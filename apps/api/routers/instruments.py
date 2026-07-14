from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from packages.services.instruments import list_instruments_payload
from packages.shared.database import get_session

router = APIRouter(prefix="/instruments", tags=["instruments"])


@router.get("")
def list_instruments(
    q: str | None = Query(default=None),
    market: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return list_instruments_payload(
        session=session,
        query=q,
        market=market,
        limit=limit,
        offset=offset,
    )
