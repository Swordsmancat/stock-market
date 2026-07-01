from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from packages.services.task_runs import enqueue_task_run
from packages.shared.database import get_session

router = APIRouter(prefix="/ingestion", tags=["ingestion"])

TASK_NAME = "ingestion.ingest_market_data"


def _enqueue_market_snapshot_ingestion(
    *,
    market: str,
    provider: str,
    start: date,
    end: date,
    session: Session,
) -> dict[str, object]:
    return enqueue_task_run(
        TASK_NAME,
        {
            "market": market,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "provider": provider,
        },
        session=session,
    )


@router.post("/snapshot")
def ingest_market_snapshot(
    market: str = Query(...),
    provider: str = Query(default="mock"),
    start: date = Query(...),
    end: date = Query(...),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return _enqueue_market_snapshot_ingestion(
        market=market,
        provider=provider,
        start=start,
        end=end,
        session=session,
    )


@router.post("/mock-snapshot")
def ingest_mock_snapshot(
    market: str = Query(...),
    provider: str = Query(default="mock"),
    start: date = Query(...),
    end: date = Query(...),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return _enqueue_market_snapshot_ingestion(
        market=market,
        provider=provider,
        start=start,
        end=end,
        session=session,
    )
