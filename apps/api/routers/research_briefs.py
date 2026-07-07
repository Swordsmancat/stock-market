from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from packages.services.research_briefs import (
    ResearchBriefGenerateInput,
    generate_and_store_research_brief,
    list_research_briefs,
)
from packages.shared.database import get_session

router = APIRouter(prefix="/research-briefs", tags=["research-briefs"])


class ResearchBriefGenerateRequest(BaseModel):
    provider: str | None = Field(default=None, max_length=64)
    locale: str = Field(default="en", max_length=8)
    title: str | None = Field(default=None, max_length=180)


@router.get("")
def list_briefs(
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return list_research_briefs(session=session, limit=limit)


@router.post("/generate")
def generate_brief(
    payload: ResearchBriefGenerateRequest,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return generate_and_store_research_brief(
        ResearchBriefGenerateInput(
            provider_name=payload.provider,
            locale=payload.locale,
            title=payload.title,
        ),
        session=session,
    )
