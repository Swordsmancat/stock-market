from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from packages.services.ingestion import normalize_symbol_list
from packages.services.instrument_universe import get_instrument_universe_status
from packages.services.research_evidence_backfill import (
    BACKFILL_TASK_NAME,
    BackfillRequest,
    create_backfill_run,
    create_resume_backfill_run,
    create_retry_failed_backfill_run,
    fail_backfill_run,
    get_backfill_payload,
    link_backfill_task_run,
    request_cancel_backfill,
)
from packages.services.task_runs import enqueue_task_run
from packages.shared.database import get_session

router = APIRouter(prefix="/ingestion", tags=["ingestion"])

TASK_NAME = "ingestion.ingest_market_data"
SYMBOL_DAILY_BARS_TASK_NAME = "ingestion.ingest_symbol_daily_bars"
SYMBOL_DAILY_BARS_BATCH_TASK_NAME = "ingestion.ingest_symbol_daily_bars_batch"
INSTRUMENT_UNIVERSE_TASK_NAME = "ingestion.sync_instrument_universe"
CN_FUND_INDEX_PIPELINE_TASK_NAME = "ingestion.sync_cn_fund_index_data"
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


class ResearchEvidenceBackfillRequest(BaseModel):
    run_kind: str = Field(default="baseline", min_length=1, max_length=32)
    market: str = Field(default="CN", min_length=1, max_length=32)
    provider: str = Field(default="akshare", min_length=1, max_length=64)
    daily_bar_policy: str = Field(default="strict", min_length=1, max_length=32)
    evidence_kinds: list[str] = Field(
        default_factory=lambda: [
            "daily_bars",
            "fundamentals",
            "technical_indicators",
        ],
        min_length=1,
        max_length=3,
    )
    start_date: date | None = None
    end_date: date | None = None
    batch_size: int = Field(default=25, ge=1, le=100)
    cohort_size: int | None = Field(default=None, ge=3, le=100)
    shard_index: int | None = Field(default=None, ge=0)
    shard_count: int | None = Field(default=None, ge=1, le=31)


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
    asset_type: str,
    session: Session,
) -> dict[str, object]:
    return enqueue_task_run(
        INSTRUMENT_UNIVERSE_TASK_NAME,
        {
            "market": market.strip().upper(),
            "provider": provider.strip().lower(),
            "asset_type": asset_type.strip().lower(),
        },
        session=session,
    )


def _enqueue_cn_fund_index_pipeline(
    *,
    lookback_days: int,
    max_symbols_per_type: int,
    session: Session,
) -> dict[str, object]:
    return enqueue_task_run(
        CN_FUND_INDEX_PIPELINE_TASK_NAME,
        {
            "provider": "akshare",
            "pipeline": "cn_fund_index_data",
            "asset_types": ["etf", "index"],
            "lookback_days": lookback_days,
            "max_symbols_per_type": max_symbols_per_type,
            "trigger": "manual",
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


def _dispatch_research_evidence_backfill(
    created: dict[str, object],
    *,
    session: Session,
) -> dict[str, object]:
    if created["status"] != "created":
        return created
    item = created["item"]
    if not isinstance(item, dict):
        raise RuntimeError("Created backfill payload is invalid.")
    run_id = str(item["id"])
    task_input = {
        "backfill_run_id": run_id,
        "market": item["market"],
        "provider": item["provider"],
        "run_kind": item["run_kind"],
    }
    dispatched = enqueue_task_run(BACKFILL_TASK_NAME, task_input, session=session)
    task_run = dispatched.get("task_run")
    if isinstance(task_run, dict) and task_run.get("id"):
        link_backfill_task_run(run_id, str(task_run["id"]), session=session)
    if dispatched["status"] != "dispatched":
        fail_backfill_run(run_id, session=session, code="BACKFILL_DISPATCH_FAILED")
    return {
        **dispatched,
        "backfill": get_backfill_payload(run_id, session=session)["item"],
    }


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
    asset_type: str = Query(default="stock", pattern="^(stock|etf|index)$"),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return _enqueue_instrument_universe_sync(
        market=market,
        provider=provider,
        asset_type=asset_type,
        session=session,
    )


@router.get("/instrument-universe/status")
def get_a_share_instrument_universe_status(
    market: str = Query(default="CN"),
    provider: str = Query(default="akshare"),
    asset_type: str = Query(default="stock", pattern="^(stock|etf|index)$"),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        return get_instrument_universe_status(
            session=session,
            market=market,
            provider_name=provider,
            asset_type=asset_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/cn-fund-index-pipeline")
def sync_cn_fund_index_pipeline(
    lookback_days: int = Query(default=120, ge=7, le=730),
    max_symbols_per_type: int = Query(default=5000, ge=1, le=5000),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return _enqueue_cn_fund_index_pipeline(
        lookback_days=lookback_days,
        max_symbols_per_type=max_symbols_per_type,
        session=session,
    )


@router.post("/corporate-actions")
def sync_corporate_actions(
    request: CorporateActionSyncRequest,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    return _enqueue_corporate_action_sync(request=request, session=session)


@router.post("/a-share-evidence-backfills")
def start_a_share_evidence_backfill(
    request: ResearchEvidenceBackfillRequest,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    try:
        created = create_backfill_run(
            BackfillRequest(
                run_kind=request.run_kind,
                market=request.market,
                provider=request.provider,
                daily_bar_policy=request.daily_bar_policy,
                evidence_kinds=tuple(request.evidence_kinds),
                start_date=request.start_date,
                end_date=request.end_date,
                batch_size=request.batch_size,
                cohort_size=request.cohort_size,
                shard_index=request.shard_index,
                shard_count=request.shard_count,
            ),
            session=session,
        )
        return _dispatch_research_evidence_backfill(created, session=session)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/a-share-evidence-backfills/{run_id}")
def get_a_share_evidence_backfill(
    run_id: str,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    payload = get_backfill_payload(run_id, session=session)
    if payload is None:
        raise HTTPException(status_code=404, detail="Research evidence backfill not found")
    return payload


@router.post("/a-share-evidence-backfills/{run_id}/resume")
def resume_a_share_evidence_backfill(
    run_id: str,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    if get_backfill_payload(run_id, session=session) is None:
        raise HTTPException(status_code=404, detail="Research evidence backfill not found")
    try:
        return _dispatch_research_evidence_backfill(
            create_resume_backfill_run(run_id, session=session),
            session=session,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/a-share-evidence-backfills/{run_id}/retry-failed")
def retry_failed_a_share_evidence_backfill(
    run_id: str,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    if get_backfill_payload(run_id, session=session) is None:
        raise HTTPException(status_code=404, detail="Research evidence backfill not found")
    try:
        return _dispatch_research_evidence_backfill(
            create_retry_failed_backfill_run(run_id, session=session),
            session=session,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/a-share-evidence-backfills/{run_id}/cancel")
def cancel_a_share_evidence_backfill(
    run_id: str,
    session: Session = Depends(get_session),
) -> dict[str, object]:
    if get_backfill_payload(run_id, session=session) is None:
        raise HTTPException(status_code=404, detail="Research evidence backfill not found")
    try:
        return request_cancel_backfill(run_id, session=session)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
    asset_type: str = Query(default="stock", description="Instrument asset type: stock, etf, or index."),
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
    asset_type: str = Query(default="stock", description="Instrument asset type: stock, etf, or index."),
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
