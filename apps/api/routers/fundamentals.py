from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from packages.services.fundamentals import get_fundamental_payload
from packages.shared.database import get_session

router = APIRouter(prefix="/fundamentals", tags=["fundamentals"])


@router.get("/{symbol}")
def get_fundamentals(
    symbol: str,
    as_of: date | None = Query(default=None),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return get_fundamental_payload(symbol, as_of=as_of, session=session)
