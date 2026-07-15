from __future__ import annotations

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from packages.services.market_assistant import answer_market_assistant_question
from packages.shared.database import get_session


router = APIRouter(prefix="/assistant", tags=["assistant"])


class MarketAssistantRequest(BaseModel):
    scope: Literal["instrument"] = "instrument"
    symbol: str = Field(..., min_length=1, max_length=32)
    question: str = Field(..., min_length=1, max_length=1000)
    locale: Literal["zh", "en"] = "zh"
    timeframe: Literal["1d"] = "1d"
    start: date | None = None
    end: date | None = None
    provider: str | None = Field(default=None, max_length=32)
    research_snapshot_id: str | None = Field(default=None, max_length=128)


@router.post("/market")
def answer_market_assistant(
    request: MarketAssistantRequest,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        return answer_market_assistant_question(
            symbol=request.symbol,
            question=request.question,
            scope=request.scope,
            locale=request.locale,
            timeframe=request.timeframe,
            start=request.start,
            end=request.end,
            provider_name=request.provider,
            research_snapshot_id=request.research_snapshot_id,
            session=session,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
