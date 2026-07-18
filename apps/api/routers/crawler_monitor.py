from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from packages.services.crawler_monitor import get_crawler_monitor
from packages.shared.database import get_session


router = APIRouter(prefix="/crawler-monitor", tags=["crawler-monitor"])


@router.get("")
def get_crawler_monitor_route(
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return get_crawler_monitor(session)
