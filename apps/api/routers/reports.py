from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from packages.services.reports import (
    generate_and_store_daily_report,
    generate_stock_report_payload,
    get_daily_report_history_payload,
    get_latest_daily_report_payload,
)
from packages.shared.database import get_session

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("")
def list_reports() -> dict[str, list[dict[str, str]]]:
    return {"items": []}


@router.post("/{symbol}/daily/generate")
def generate_daily_report(
    symbol: str,
    start: date = Query(...),
    end: date = Query(...),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return generate_and_store_daily_report(symbol, start, end, session=session)


@router.get("/{symbol}/daily/latest")
def get_latest_daily_report(
    symbol: str,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return get_latest_daily_report_payload(symbol, session=session)


@router.get("/{symbol}/daily/history")
def get_daily_report_history(
    symbol: str,
    limit: int = Query(default=10, ge=1, le=100),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return get_daily_report_history_payload(symbol, session=session, limit=limit)


@router.get("/{symbol}/stock")
def generate_stock_report(
    symbol: str,
    start: date = Query(...),
    end: date = Query(...),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return generate_stock_report_payload(symbol, start, end, session=session)
