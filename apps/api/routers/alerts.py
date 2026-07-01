from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from packages.services.alert_triggers import list_recent_alert_triggers_payload
from packages.shared.database import get_session

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/triggers/recent")
def list_recent_alert_triggers(
    limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return list_recent_alert_triggers_payload(session=session, limit=limit)
