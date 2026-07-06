from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from packages.services.research_source_notes import (
    ResearchSourceNoteInput,
    ResearchSourceNoteValidationError,
    create_research_source_note,
    list_research_source_notes,
)
from packages.shared.cache import clear_market_overview_cache
from packages.shared.database import get_session

router = APIRouter(prefix="/research-source-notes", tags=["research-source-notes"])


class ResearchSourceNoteCreateInput(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    source_name: str = Field(min_length=1, max_length=256)
    source_type: str = Field(min_length=1, max_length=64)
    source_url: str | None = Field(default=None, max_length=1024)
    symbols: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    published_at: datetime | None = None
    as_of: date | None = None
    retrieved_at: datetime | None = None
    excerpt: str | None = None
    note: str | None = None
    ai_follow_up: str | None = None
    review_status: str = "draft"
    is_citable: bool = False
    metadata: dict[str, object] = Field(default_factory=dict)
    source_id: str | None = Field(default=None, max_length=128)
    source_label: str | None = Field(default=None, max_length=256)
    source_category: str | None = Field(default=None, max_length=64)
    target_indicator_codes: list[str] = Field(default_factory=list)
    component_role: str | None = Field(default=None, max_length=64)
    methodology_note: str | None = None
    license_note: str | None = None


@router.get("")
def list_notes(
    limit: int = Query(default=50, ge=1, le=200),
    review_status: str | None = None,
    source_type: str | None = None,
    citable_only: bool = False,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return list_research_source_notes(
        session=session,
        limit=limit,
        review_status=review_status,
        source_type=source_type,
        citable_only=citable_only,
    )


@router.post("")
def create_note(
    payload: ResearchSourceNoteCreateInput,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        note = create_research_source_note(
            ResearchSourceNoteInput(
                title=payload.title,
                source_name=payload.source_name,
                source_type=payload.source_type,
                source_url=payload.source_url,
                symbols=payload.symbols,
                tags=payload.tags,
                published_at=payload.published_at,
                as_of=payload.as_of,
                retrieved_at=payload.retrieved_at,
                excerpt=payload.excerpt,
                note=payload.note,
                ai_follow_up=payload.ai_follow_up,
                review_status=payload.review_status,
                is_citable=payload.is_citable,
                metadata=payload.metadata,
                source_id=payload.source_id,
                source_label=payload.source_label,
                source_category=payload.source_category,
                target_indicator_codes=payload.target_indicator_codes,
                component_role=payload.component_role,
                methodology_note=payload.methodology_note,
                license_note=payload.license_note,
            ),
            session=session,
        )
    except ResearchSourceNoteValidationError as error:
        raise HTTPException(status_code=422, detail={"errors": error.errors}) from error

    note["cache"] = {"market_overview_cleared": clear_market_overview_cache()}
    return note
