from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from packages.services.market_indicators import (
    MarketIndicatorSeedImportError,
    MarketIndicatorSeedOverwriteRequiredError,
    import_market_indicator_observation_seed_content,
    preview_market_indicator_observation_seed_content,
)
from packages.shared.cache import clear_market_overview_cache
from packages.shared.database import get_session

router = APIRouter(prefix="/market-indicators", tags=["market-indicators"])


class MarketIndicatorSeedContentInput(BaseModel):
    content: str = Field(min_length=1)
    format: str = "auto"
    filename: str | None = None
    overwrite_acknowledged: bool = False


@router.post("/seeds/preview")
def preview_market_indicator_seeds(
    payload: MarketIndicatorSeedContentInput,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return preview_market_indicator_observation_seed_content(
        payload.content,
        session=session,
        format_hint=payload.format,
        filename=payload.filename,
    )


@router.post("/seeds/import")
def import_market_indicator_seeds(
    payload: MarketIndicatorSeedContentInput,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    preview = preview_market_indicator_observation_seed_content(
        payload.content,
        session=session,
        format_hint=payload.format,
        filename=payload.filename,
    )
    if not preview["can_import"]:
        raise HTTPException(status_code=422, detail=preview)

    summary = preview["summary"] if isinstance(preview["summary"], dict) else {}
    if int(summary.get("updates") or 0) > 0 and not payload.overwrite_acknowledged:
        raise HTTPException(status_code=409, detail=preview)

    try:
        result = import_market_indicator_observation_seed_content(
            payload.content,
            session=session,
            format_hint=payload.format,
            filename=payload.filename,
            overwrite_acknowledged=payload.overwrite_acknowledged,
        )
    except MarketIndicatorSeedOverwriteRequiredError as error:
        raise HTTPException(status_code=409, detail=error.preview) from error
    except MarketIndicatorSeedImportError as error:
        raise HTTPException(status_code=422, detail={"errors": error.errors}) from error

    result["cache"] = {"market_overview_cleared": clear_market_overview_cache()}
    return result
