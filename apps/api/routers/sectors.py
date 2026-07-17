"""API router for sector/industry analysis."""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from packages.providers.eastmoney_industry_rankings import EastmoneyIndustryRankingError
from packages.services.industry_rankings import get_industry_ranking_payload, refresh_industry_rankings
from packages.services.hot_sectors import get_hot_sectors_payload
from packages.shared.database import get_session


router = APIRouter()


@router.get("/sectors/hot")
async def get_hot_sectors(
    limit: int = Query(5, ge=1, le=10, description="Number of sectors to return"),
    provider: str | None = Query(default=None, description="Optional hot-sector fund-flow provider"),
    sector_type: str | None = Query(
        default=None,
        description="Optional sector taxonomy to rank: industry or concept",
    ),
    window: str | None = Query(
        default=None,
        description="Optional fund-flow window: today, 5d, or 10d",
    ),
) -> dict[str, object]:
    """
    Get hot sectors based on recent performance.

    Returns top performing sectors with their performance metrics.
    """
    return get_hot_sectors_payload(
        limit=limit,
        provider_name=provider,
        sector_type=sector_type,
        window=window,
    )


@router.get("/sectors/industry-rankings")
def get_industry_rankings(days: int = Query(12, ge=1, le=20), limit: int = Query(20, ge=1, le=20), session: Session = Depends(get_session)) -> dict[str, object]:
    return get_industry_ranking_payload(session=session, days=days, limit=limit)


@router.post("/sectors/industry-rankings/refresh")
def refresh_stored_industry_rankings(days: int = Query(12, ge=1, le=20), session: Session = Depends(get_session)):
    try:
        return refresh_industry_rankings(session=session, days=days)
    except EastmoneyIndustryRankingError as error:
        return JSONResponse(status_code=502, content={"detail": {"code": error.code, "message": "Eastmoney industry data is temporarily unavailable; stored history was preserved."}})
