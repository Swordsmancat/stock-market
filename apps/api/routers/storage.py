from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from packages.services.storage_overview import (
    StorageOverviewUnavailable,
    get_storage_overview,
)
from packages.shared.database import get_session

router = APIRouter(prefix="/storage", tags=["storage"])


@router.get("/overview")
def get_storage_overview_route(
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        return get_storage_overview(session)
    except StorageOverviewUnavailable as error:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "message": "Database storage statistics are unavailable.",
            },
        ) from error
