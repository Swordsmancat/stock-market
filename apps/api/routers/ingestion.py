from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from packages.services.task_runs import enqueue_task_run
from packages.shared.database import get_session

router = APIRouter(prefix="/ingestion", tags=["ingestion"])

TASK_NAME = "ingestion.ingest_market_data"
SYMBOL_DAILY_BARS_TASK_NAME = "ingestion.ingest_symbol_daily_bars"


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


def _normalize_optional_query_value(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _enqueue_symbol_daily_bars_ingestion(
    *,
    symbol: str,
    market: str,
    provider: str | None,
    start: date,
    end: date,
    exchange: str | None,
    timeframe: str,
    asset_type: str,
    session: Session,
) -> dict[str, object]:
    task_input = {
        "symbol": symbol.strip().upper(),
        "market": market.strip().upper(),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "timeframe": timeframe.strip().lower(),
        "asset_type": asset_type.strip().lower() or "stock",
    }
    normalized_provider = _normalize_optional_query_value(provider)
    normalized_exchange = _normalize_optional_query_value(exchange)
    if normalized_provider is not None:
        task_input["provider"] = normalized_provider
    if normalized_exchange is not None:
        task_input["exchange"] = normalized_exchange

    return enqueue_task_run(
        SYMBOL_DAILY_BARS_TASK_NAME,
        task_input,
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


@router.post("/symbol-daily-bars")
def ingest_symbol_daily_bars(
    symbol: str = Query(...),
    market: str = Query(...),
    provider: str | None = Query(default=None),
    start: date = Query(...),
    end: date = Query(...),
    exchange: str | None = Query(default=None),
    timeframe: str = Query(default="1d"),
    asset_type: str = Query(default="stock", description="Instrument asset type: stock or etf."),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return _enqueue_symbol_daily_bars_ingestion(
        symbol=symbol,
        market=market,
        provider=provider,
        start=start,
        end=end,
        exchange=exchange,
        timeframe=timeframe,
        asset_type=asset_type,
        session=session,
    )
