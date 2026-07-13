from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.orm import Session

from apps.api.routers.stock_selection import StockSelectionOverrides
from packages.services.research_shortlists import (
    ResearchShortlistGenerateInput,
    ResearchShortlistReadinessError,
    generate_research_shortlist,
    get_latest_research_shortlist,
    get_research_shortlist,
)
from packages.services.research_shortlist_outcomes import (
    evaluate_research_shortlist_outcomes,
    get_research_shortlist_outcome_tracking,
    get_research_shortlist_outcomes,
)
from packages.shared.database import get_session


router = APIRouter(prefix="/research-shortlists", tags=["research-shortlists"])


class ResearchShortlistGenerateRequest(BaseModel):
    profile_id: str = Field(default="balanced_research", min_length=1, max_length=64)
    overrides: dict[str, object] = Field(default_factory=dict)
    market: str = Field(default="CN", min_length=1, max_length=32)
    asset_type: str = Field(default="stock", min_length=1, max_length=32)
    shortlist_limit: int = Field(default=10, ge=1, le=20)
    locale: Literal["zh", "en"] = "zh"
    use_llm: bool = True


class ResearchShortlistOutcomeEvaluateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of: date | None = None


@router.post("/generate")
def generate_daily_research_shortlist(
    request: ResearchShortlistGenerateRequest,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        overrides = _validated_overrides(request.overrides)
        return generate_research_shortlist(
            ResearchShortlistGenerateInput(
                profile_id=request.profile_id,
                overrides=overrides,
                market=request.market,
                asset_type=request.asset_type,
                shortlist_limit=request.shortlist_limit,
                locale=request.locale,
                use_llm=request.use_llm,
            ),
            session=session,
        )
    except ResearchShortlistReadinessError as exc:
        raise HTTPException(status_code=409, detail=exc.as_detail()) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/latest")
def latest_daily_research_shortlist(
    market: str = Query(default="CN"),
    profile_id: str = Query(default="balanced_research"),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        return get_latest_research_shortlist(
            session=session,
            market=market,
            profile_id=profile_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/tracking")
def research_shortlist_outcome_tracking(
    market: str = Query(default="CN"),
    profile_id: str = Query(default="balanced_research"),
    limit: int = Query(default=10, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    as_of: date | None = Query(default=None),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        return get_research_shortlist_outcome_tracking(
            session=session,
            market=market,
            profile_id=profile_id,
            limit=limit,
            offset=offset,
            as_of=as_of,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{run_id}/outcomes/evaluate")
def evaluate_research_shortlist_outcome_detail(
    run_id: str,
    request: ResearchShortlistOutcomeEvaluateRequest | None = None,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        payload = evaluate_research_shortlist_outcomes(
            run_id,
            session=session,
            as_of=request.as_of if request is not None else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if payload is None:
        raise HTTPException(status_code=404, detail="Research shortlist not found")
    return payload


@router.get("/{run_id}/outcomes")
def research_shortlist_outcome_detail(
    run_id: str,
    as_of: date | None = Query(default=None),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        payload = get_research_shortlist_outcomes(
            run_id,
            session=session,
            as_of=as_of,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if payload is None:
        raise HTTPException(status_code=404, detail="Research shortlist not found")
    return payload


@router.get("/{run_id}")
def research_shortlist_detail(
    run_id: str,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    payload = get_research_shortlist(run_id, session=session)
    if payload is None:
        raise HTTPException(status_code=404, detail="Research shortlist not found")
    return payload


def _validated_overrides(overrides: dict[str, object]) -> dict[str, object]:
    try:
        validated = StockSelectionOverrides.model_validate(overrides).model_dump(exclude_none=True)
    except ValidationError as exc:
        first_error = exc.errors(include_url=False)[0]
        location = ".".join(str(part) for part in first_error.get("loc", ()))
        message = str(first_error.get("msg") or "Invalid value")
        raise ValueError(f"Invalid stock-selection override {location}: {message}") from exc
    unsupported = {
        key: value
        for key, value in overrides.items()
        if key not in StockSelectionOverrides.model_fields
    }
    return {**validated, **unsupported}
