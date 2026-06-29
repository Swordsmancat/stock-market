from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from packages.services.ingestion import ingest_mock_market_snapshot
from packages.shared.database import get_session

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/mock-snapshot")
def ingest_mock_snapshot(
    market: str = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return ingest_mock_market_snapshot(market, start, end, session=session)
