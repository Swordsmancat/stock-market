from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from packages.services.ingestion import normalize_symbol_list
from packages.services.instrument_universe import get_instrument_universe_status
from packages.services.task_runs import enqueue_task_run
from packages.shared.database import get_session

router = APIRouter(prefix="/ingestion", tags=["ingestion"])

TASK_NAME = "ingestion.ingest_market_data"
SYMBOL_DAILY_BARS_TASK_NAME = "ingestion.ingest_symbol_daily_bars"
SYMBOL_DAILY_BARS_BATCH_TASK_NAME = "ingestion.ingest_symbol_daily_bars_batch"
INSTRUMENT_UNIVERSE_TASK_NAME = "ingestion.sync_instrument_universe"
CORPORATE_ACTIONS_TASK_NAME = "ingestion.sync_corporate_actions"


class CorporateActionSyncRequest(BaseModel):
    report_period: date
    market: str = Field(default="CN", min_length=1, max_length=32)
    provider: str = Field(default="akshare", min_length=1, max_length=64)
    symbols: list[str] = Field(default_factory=list, max_length=100)
    event_types: list[str] = Field(
        default_factory=lambda: ["dividend_bonus", "rights_allotment"],
        min_length=1,
        max_length=2,
    )
    cursor: int = Field(default=0, ge=0)
    batch_size: int = Field(default=50, ge=1, le=100)


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


def _enqueue_instrument_universe_sync(
    *,
    market: str,
    provider: str,
    session: Session,
) -> dict[str, object]:
    return enqueue_task_run(
        INSTRUMENT_UNIVERSE_TASK_NAME,
        {
            "market": market.strip().upper(),
            "provider": provider.strip().lower(),
        },
        session=session,
    )


def _enqueue_corporate_action_sync(
    *,
    request: CorporateActionSyncRequest,
    session: Session,
) -> dict[str, object]:
    return enqueue_task_run(
        CORPORATE_ACTIONS_TASK_NAME,
        {
            "report_period": request.report_period.isoformat(),
            "market": request.market.strip().upper(),
            "provider": request.provider.strip().lower(),
            "symbols": sorted(
                {symbol.strip().upper() for symbol in request.symbols if symbol.strip()}
            ),
            "event_types": list(dict.fromkeys(request.event_types)),
            "cursor": request.cursor,
            "batch_size": request.batch_size,
        },
        session=session,
    )


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


def _enqueue_symbol_daily_bars_batch_ingestion(
    *,
    symbols: str,
    market: str,
    provider: str | None,
    start: date,
    end: date,
    exchange: str | None,
    timeframe: str,
    asset_type: str,
    session: Session,
) -> dict[str, object]:
    try:
        normalized_symbols = normalize_symbol_list(symbols)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    task_input = {
        "symbols": normalized_symbols,
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
        SYMBOL_DAILY_BARS_BATCH_TASK_NAME,
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


@router.post("/instrument-universe")
def sync_a_share_instrument_universe(
    market: str = Query(default="CN"),
    provider: str = Query(default="akshare"),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return _enqueue_instrument_universe_sync(
        market=market,
        provider=provider,
        session=session,
    )


@router.get("/instrument-universe/status")
def get_a_share_instrument_universe_status(
    market: str = Query(default="CN"),
    provider: str = Query(default="akshare"),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        return get_instrument_universe_status(
            session=session,
            market=market,
            provider_name=provider,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/corporate-actions")
def sync_corporate_actions(
    request: CorporateActionSyncRequest,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return _enqueue_corporate_action_sync(request=request, session=session)


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


@router.post("/symbol-daily-bars-batch")
def ingest_symbol_daily_bars_batch(
    symbols: str = Query(..., description="Comma-separated symbols to ingest."),
    market: str = Query(...),
    provider: str | None = Query(default=None),
    start: date = Query(...),
    end: date = Query(...),
    exchange: str | None = Query(default=None),
    timeframe: str = Query(default="1d"),
    asset_type: str = Query(default="stock", description="Instrument asset type: stock or etf."),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return _enqueue_symbol_daily_bars_batch_ingestion(
        symbols=symbols,
        market=market,
        provider=provider,
        start=start,
        end=end,
        exchange=exchange,
        timeframe=timeframe,
        asset_type=asset_type,
        session=session,
    )
