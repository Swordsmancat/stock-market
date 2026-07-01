from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from packages.services.market_data import (
    get_bars_payload,
    get_indicator_payload,
    get_latest_bar_payload,
    get_latest_bars_batch_payload,
)
from packages.shared.database import get_session

router = APIRouter(prefix="/market-data", tags=["market-data"])


@router.get("/latest")
def get_latest_bars(
    symbols: str = Query(..., description="Comma-separated symbols, e.g. AAPL,600519"),
    provider: str = Query(default="mock"),
    session: Session = Depends(get_session),
) -> dict:
    symbol_list = [symbol.strip().upper() for symbol in symbols.split(",") if symbol.strip()]
    return get_latest_bars_batch_payload(symbol_list, session=session, provider_name=provider)


@router.get("/{symbol}/latest")
def get_latest_bar(
    symbol: str,
    provider: str = Query(default="mock"),
    session: Session = Depends(get_session),
) -> dict:
    return get_latest_bar_payload(symbol, session=session, provider_name=provider)


@router.get("/{symbol}/bars")
def get_bars(
    symbol: str,
    timeframe: str = Query(default="1d"),
    start: date = Query(...),
    end: date = Query(...),
    provider: str = Query(default="mock"),
    session: Session = Depends(get_session),
) -> dict:
    return get_bars_payload(symbol, timeframe, start, end, session=session, provider_name=provider)


@router.get("/{symbol}/indicators")
def get_indicators(
    symbol: str,
    start: date = Query(...),
    end: date = Query(...),
    ma_window: int = Query(default=20, ge=1),
    session: Session = Depends(get_session),
) -> dict:
    return get_indicator_payload(symbol, start, end, ma_window, session=session)
