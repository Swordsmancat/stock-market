from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from packages.services.reports import (
    generate_and_store_daily_report,
    generate_stock_report_payload,
    get_daily_report_history_payload,
    get_latest_daily_report_payload,
    get_report_payload,
    list_reports_payload,
)
from packages.shared.database import get_session

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("")
def list_reports(
    symbol: str | None = Query(default=None),
    report_type: str | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return list_reports_payload(
        session=session,
        symbol=symbol,
        report_type=report_type,
        query=q,
        limit=limit,
        offset=offset,
    )


@router.get("/items/{report_id}")
def get_report(report_id: str, session: Session = Depends(get_session)) -> dict[str, object]:
    report = get_report_payload(report_id, session=session)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


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
