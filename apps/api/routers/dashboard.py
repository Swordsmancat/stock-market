from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from packages.services.market_dashboard import get_market_overview_payload
from packages.shared.database import get_session

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/market-overview")
def get_market_overview(
    provider: str | None = Query(default=None),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return get_market_overview_payload(session=session, provider_name=provider)
