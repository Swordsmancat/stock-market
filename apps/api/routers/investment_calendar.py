from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from packages.services.investment_calendar import get_investment_calendar_payload
from packages.shared.database import get_session


router = APIRouter(prefix="/investment-calendar", tags=["investment-calendar"])


@router.get("")
def get_investment_calendar(
    start: date,
    end: date,
    kind: Literal["economic", "company"] = "economic",
    min_importance: int = Query(default=0, ge=0, le=5),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        return get_investment_calendar_payload(
            session=session,
            start=start,
            end=end,
            kind=kind,
            min_importance=min_importance,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
