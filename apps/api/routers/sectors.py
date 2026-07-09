"""API router for sector/industry analysis."""

from fastapi import APIRouter, Query

from packages.services.hot_sectors import get_hot_sectors_payload


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
