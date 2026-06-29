from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from packages.services.reports import generate_stock_report_payload
from packages.shared.database import get_session

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("")
def list_reports() -> dict[str, list[dict[str, str]]]:
    return {"items": []}


@router.get("/{symbol}/stock")
def generate_stock_report(
    symbol: str,
    start: date = Query(...),
    end: date = Query(...),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return generate_stock_report_payload(symbol, start, end, session=session)
