from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from packages.services.topic_research import get_topic_research_payload
from packages.shared.database import get_session


router = APIRouter(prefix="/topic-research", tags=["topic-research"])


@router.get("")
def get_topic_research(
    topic: Literal["agriculture", "consumption", "real_estate", "nonferrous"] = Query(
        default="agriculture"
    ),
    window: Literal["30d", "90d", "180d"] = Query(default="90d"),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        return get_topic_research_payload(session=session, topic=topic, window=window)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
