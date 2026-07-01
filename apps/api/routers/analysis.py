from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from packages.services.task_runs import enqueue_task_run
from packages.shared.database import get_session

router = APIRouter(prefix="/analysis", tags=["analysis"])

TASK_NAME = "reports.refresh_daily_stock_analysis"


@router.post("/refresh")
def refresh_analysis(
    symbol: str = Query(...),
    market: str = Query(...),
    start: date = Query(...),
    end: date = Query(...),
    ma_window: int = Query(default=20, ge=1),
    provider: str = Query(default="mock"),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return enqueue_task_run(
        TASK_NAME,
        {
            "symbol": symbol,
            "market": market,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "ma_window": ma_window,
            "provider": provider,
        },
        session=session,
    )
