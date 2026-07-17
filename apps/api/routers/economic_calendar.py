from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from packages.providers.eastmoney_economic_calendar import EastmoneyEconomicCalendarError
from packages.services.economic_calendar import (
    get_economic_calendar_payload,
    refresh_economic_calendar,
)
from packages.shared.database import get_session

router = APIRouter(prefix="/economic-calendar", tags=["economic-calendar"])


class RefreshInput(BaseModel):
    start: date
    end: date
    dry_run: bool = False


@router.get("/events")
def get_events(
    start: date,
    end: date,
    min_importance: int = Query(default=0, ge=0, le=5),
    country: str | None = Query(default=None, max_length=64),
    limit: int = Query(default=200, ge=1, le=200),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        return get_economic_calendar_payload(
            session=session,
            start=start,
            end=end,
            min_importance=min_importance,
            country=country,
            limit=limit,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/refresh")
def refresh_events(
    payload: RefreshInput, session: Session = Depends(get_session)
) -> dict[str, object]:
    try:
        result = refresh_economic_calendar(
            session=session, start=payload.start, end=payload.end, dry_run=payload.dry_run
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except EastmoneyEconomicCalendarError as error:
        raise HTTPException(
            status_code=502, detail={"status": "error", "provider": "eastmoney", "code": error.code}
        ) from error
    return {
        "status": "ok",
        "provider": "eastmoney",
        "fetched": result.fetched,
        "inserted": result.inserted,
        "updated": result.updated,
        "dry_run": result.dry_run,
    }
