from datetime import date as Date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from packages.services.market_daily_evidence import (
    DEFAULT_MARKET_DAILY_EVIDENCE_EVENT_TYPES,
    MarketDailyEvidenceImportInput,
    MarketDailyEvidenceValidationError,
    SUPPORTED_MARKET_DAILY_EVIDENCE_EVENT_TYPES,
    import_market_daily_evidence,
    list_market_daily_evidence,
)
from packages.shared.cache import clear_market_overview_cache
from packages.shared.database import get_session


router = APIRouter(prefix="/market-daily-evidence", tags=["market-daily-evidence"])


class MarketDailyEvidenceImportRequest(BaseModel):
    date: Date | None = None
    market: str = Field(default="CN", min_length=1, max_length=32)
    provider: str | None = Field(default=None, max_length=64)
    event_types: list[str] = Field(
        default_factory=lambda: list(DEFAULT_MARKET_DAILY_EVIDENCE_EVENT_TYPES),
        min_length=1,
        max_length=len(SUPPORTED_MARKET_DAILY_EVIDENCE_EVENT_TYPES),
    )
    limit: int = Field(default=20, ge=1, le=100)


@router.get("")
def list_evidence(
    event_type: str | None = None,
    identity: str | None = None,
    symbol: str | None = None,
    market: str | None = None,
    trade_date: Date | None = Query(default=None, alias="date"),
    citable_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        return list_market_daily_evidence(
            session=session,
            event_type=event_type,
            identity=identity,
            symbol=symbol,
            market=market,
            trade_date=trade_date,
            citable_only=citable_only,
            limit=limit,
        )
    except MarketDailyEvidenceValidationError as error:
        raise HTTPException(status_code=422, detail={"errors": error.errors}) from error


@router.post("/import")
def import_evidence(
    payload: MarketDailyEvidenceImportRequest,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        result = import_market_daily_evidence(
            MarketDailyEvidenceImportInput(
                trade_date=payload.date,
                market=payload.market,
                provider_name=payload.provider,
                event_types=tuple(payload.event_types),
                limit=payload.limit,
            ),
            session=session,
        )
    except MarketDailyEvidenceValidationError as error:
        raise HTTPException(status_code=422, detail={"errors": error.errors}) from error

    result["cache"] = {
        "market_overview_cleared": clear_market_overview_cache()
        if result.get("status") != "failed"
        else False,
    }
    return result
