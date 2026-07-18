from datetime import date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from apps.worker.celery_app import celery_app
from packages.domain.models import TaskRun
from packages.services.corporate_actions import (
    CorporateActionSyncInput,
    sync_corporate_action_evidence,
)
from packages.services.cn_fund_index_pipeline import (
    CN_FUND_INDEX_PIPELINE_TASK_NAME,
    CnFundIndexPipelineError,
    sync_cn_fund_index_data,
)
from packages.services.daily_bar_sources import STRICT_POLICY
from packages.services.eastmoney_automation import (
    EASTMONEY_CALENDAR_TASK_NAME,
    EASTMONEY_FUNDAMENTALS_TASK_NAME,
    EASTMONEY_INDUSTRY_TASK_NAME,
    EASTMONEY_NEWS_TASK_NAME,
    EastmoneyAutomationError,
    refresh_eastmoney_calendar_batch,
    refresh_eastmoney_fundamentals_batch,
    refresh_eastmoney_industry_batch,
    refresh_eastmoney_news_batch,
)
from packages.services.ingestion import (
    ingest_market_snapshot,
    ingest_symbol_daily_bars,
    ingest_symbol_daily_bars_batch,
    normalize_symbol_list,
)
from packages.services.instrument_universe import sync_instrument_universe
from packages.services.official_disclosure_operations import (
    WATCHLIST_DISCLOSURE_SCHEDULE_TASK_NAME,
    WATCHLIST_DISCLOSURE_TASK_NAME,
    enqueue_watchlist_official_disclosure_ingestion,
    ingest_watchlist_official_disclosures,
)
from packages.services.research_evidence_backfill import (
    BACKFILL_TASK_NAME,
    BackfillRequest,
    create_backfill_run,
    execute_backfill_run,
    fail_backfill_run,
    link_backfill_task_run,
)
from packages.services.task_runs import (
    enqueue_task_run,
    fail_task_run,
    finish_task_run,
    start_task_run,
    update_task_run_progress,
)
from packages.shared.config import settings
from packages.shared.database import SessionLocal


def _run_eastmoney_automation_task(
    *,
    task_name: str,
    pipeline: str,
    trigger: str,
    task_run_id: str | None,
    operation,
) -> dict[str, object]:
    session = SessionLocal()
    task_run = None
    try:
        if task_run_id:
            task_run = session.get(TaskRun, UUID(task_run_id))
            if task_run is None:
                raise ValueError("Invalid task run identity.")
        else:
            cutoff = datetime.now(ZoneInfo("UTC")) - timedelta(
                minutes=settings.task_run_stale_minutes
            )
            active = (
                session.query(TaskRun)
                .filter(TaskRun.task_name == task_name)
                .filter(TaskRun.status == "running")
                .filter(TaskRun.heartbeat_at >= cutoff)
                .first()
            )
            if active is not None:
                return {
                    "status": "skipped",
                    "provider": "eastmoney_public",
                    "pipeline": pipeline,
                    "code": "ALREADY_RUNNING",
                }
            task_run = start_task_run(
                task_name,
                {
                    "provider": "eastmoney_public",
                    "pipeline": pipeline,
                    "trigger": trigger,
                },
                session=session,
            )

        def report_progress(phase: str, current: int, total: int, message: str) -> None:
            update_task_run_progress(
                task_run,
                phase=phase,
                current=current,
                total=total,
                message=message,
                session=session,
            )

        result = operation(session, report_progress)
        finish_task_run(task_run, result, session=session)
        return result
    except Exception as error:
        session.rollback()
        if task_run is not None and task_run.status == "running":
            code = (
                error.code
                if isinstance(error, EastmoneyAutomationError)
                else "EASTMONEY_AUTOMATION_FAILED"
            )
            fail_task_run(task_run, code, session=session)
        raise
    finally:
        session.close()


@celery_app.task(name=EASTMONEY_CALENDAR_TASK_NAME)
def refresh_eastmoney_economic_calendar_task(
    trigger: str = "manual",
    task_run_id: str | None = None,
) -> dict[str, object]:
    return _run_eastmoney_automation_task(
        task_name=EASTMONEY_CALENDAR_TASK_NAME,
        pipeline="economic_calendar",
        trigger=trigger,
        task_run_id=task_run_id,
        operation=lambda session, progress: refresh_eastmoney_calendar_batch(
            session=session,
            progress_callback=progress,
            max_attempts=settings.eastmoney_max_transient_attempts,
            retry_base_seconds=settings.eastmoney_retry_base_seconds,
        ),
    )


@celery_app.task(name=EASTMONEY_INDUSTRY_TASK_NAME)
def refresh_eastmoney_industry_rankings_task(
    trigger: str = "manual",
    task_run_id: str | None = None,
) -> dict[str, object]:
    return _run_eastmoney_automation_task(
        task_name=EASTMONEY_INDUSTRY_TASK_NAME,
        pipeline="industry_rankings",
        trigger=trigger,
        task_run_id=task_run_id,
        operation=lambda session, progress: refresh_eastmoney_industry_batch(
            session=session,
            progress_callback=progress,
            max_attempts=settings.eastmoney_max_transient_attempts,
            retry_base_seconds=settings.eastmoney_retry_base_seconds,
        ),
    )


@celery_app.task(name=EASTMONEY_NEWS_TASK_NAME)
def refresh_eastmoney_research_news_task(
    trigger: str = "manual",
    task_run_id: str | None = None,
) -> dict[str, object]:
    return _run_eastmoney_automation_task(
        task_name=EASTMONEY_NEWS_TASK_NAME,
        pipeline="research_news",
        trigger=trigger,
        task_run_id=task_run_id,
        operation=lambda session, progress: refresh_eastmoney_news_batch(
            session=session,
            limit=settings.eastmoney_research_batch_size,
            request_delay_seconds=max(0, settings.eastmoney_request_delay_ms) / 1000,
            progress_callback=progress,
        ),
    )


@celery_app.task(name=EASTMONEY_FUNDAMENTALS_TASK_NAME)
def refresh_eastmoney_research_fundamentals_task(
    trigger: str = "manual",
    task_run_id: str | None = None,
) -> dict[str, object]:
    return _run_eastmoney_automation_task(
        task_name=EASTMONEY_FUNDAMENTALS_TASK_NAME,
        pipeline="research_fundamentals",
        trigger=trigger,
        task_run_id=task_run_id,
        operation=lambda session, progress: refresh_eastmoney_fundamentals_batch(
            session=session,
            limit=settings.eastmoney_research_batch_size,
            request_delay_seconds=max(0, settings.eastmoney_request_delay_ms) / 1000,
            progress_callback=progress,
            max_attempts=settings.eastmoney_max_transient_attempts,
            retry_base_seconds=settings.eastmoney_retry_base_seconds,
        ),
    )


def _extract_quality_diagnostics(snapshot: dict[str, object]) -> dict[str, object]:
    quality_diagnostics = snapshot.get("quality_diagnostics")
    if isinstance(quality_diagnostics, dict):
        return quality_diagnostics

    return {
        "status": "FAIL",
        "instrument_count": 0,
        "instruments": [],
        "errors": [
            {
                "code": "QUALITY_DIAGNOSTICS_MISSING",
                "message": "Ingestion completed without quality diagnostics.",
            },
        ],
        "warnings": [],
    }


@celery_app.task(name="ingestion.ingest_market_data")
def ingest_market_data(
    market: str,
    start: str | None = None,
    end: str | None = None,
    provider: str | None = None,
    task_run_id: str | None = None,
) -> dict[str, object]:
    end_date = date.fromisoformat(end) if end else date.today()
    start_date = date.fromisoformat(start) if start else end_date - timedelta(days=2)
    provider_value = provider or settings.market_data_provider
    session = SessionLocal()

    if task_run_id:
        task_run = session.get(TaskRun, UUID(task_run_id))
        if task_run is None:
            session.close()
            msg = f"Task run not found: {task_run_id}"
            raise ValueError(msg)
    else:
        task_run = start_task_run(
            "ingestion.ingest_market_data",
            {
                "market": market,
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "provider": provider_value,
            },
            session=session,
        )

    try:
        snapshot = ingest_market_snapshot(
            market,
            start_date,
            end_date,
            session=session,
            provider_name=provider_value,
        )
        result_payload = {
            "market": str(snapshot["market"]),
            "instrument_count": int(snapshot["instrument_count"]),
            "bar_count": int(snapshot["bar_count"]),
            "status": str(snapshot["status"]),
            "provider": provider_value,
            "quality_diagnostics": _extract_quality_diagnostics(snapshot),
        }
        finish_task_run(task_run, result_payload, session=session)
        return result_payload
    except Exception as exc:
        fail_task_run(task_run, str(exc), session=session)
        raise
    finally:
        session.close()


@celery_app.task(name="ingestion.ingest_mock_market_data")
def ingest_mock_market_data(
    market: str,
    start: str | None = None,
    end: str | None = None,
    provider: str | None = None,
) -> dict[str, object]:
    return ingest_market_data(
        market=market,
        start=start,
        end=end,
        provider=provider or "mock",
    )


@celery_app.task(name="ingestion.ingest_symbol_daily_bars")
def ingest_symbol_daily_bars_task(
    symbol: str,
    market: str,
    start: str | None = None,
    end: str | None = None,
    provider: str | None = None,
    exchange: str | None = None,
    timeframe: str = "1d",
    asset_type: str = "stock",
    task_run_id: str | None = None,
) -> dict[str, object]:
    end_date = date.fromisoformat(end) if end else date.today()
    start_date = date.fromisoformat(start) if start else end_date - timedelta(days=2)
    normalized_symbol = symbol.strip().upper()
    normalized_market = market.strip().upper()
    session = SessionLocal()

    if task_run_id:
        task_run = session.get(TaskRun, UUID(task_run_id))
        if task_run is None:
            session.close()
            msg = f"Task run not found: {task_run_id}"
            raise ValueError(msg)
    else:
        task_run = start_task_run(
            "ingestion.ingest_symbol_daily_bars",
            {
                "symbol": normalized_symbol,
                "market": normalized_market,
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "provider": provider,
                "exchange": exchange,
                "timeframe": timeframe,
                "asset_type": asset_type,
            },
            session=session,
        )

    try:
        ingestion_result = ingest_symbol_daily_bars(
            symbol=normalized_symbol,
            market=normalized_market,
            start=start_date,
            end=end_date,
            session=session,
            provider_name=provider,
            exchange=exchange,
            timeframe=timeframe,
            asset_type=asset_type,
        )
        result_payload = {
            "symbol": str(ingestion_result["symbol"]),
            "market": str(ingestion_result["market"]),
            "asset_type": str(ingestion_result["instruments"][0]["asset_type"]),
            "instrument_count": int(ingestion_result["instrument_count"]),
            "bar_count": int(ingestion_result["bar_count"]),
            "status": str(ingestion_result["status"]),
            "provider": str(ingestion_result["provider"]),
            "requested_provider": ingestion_result.get("requested_provider"),
            "effective_provider": str(ingestion_result["effective_provider"]),
            "timeframe": str(ingestion_result["timeframe"]),
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "no_data_reason": ingestion_result.get("no_data_reason"),
            "quality_diagnostics": _extract_quality_diagnostics(ingestion_result),
        }
        finish_task_run(task_run, result_payload, session=session)
        return result_payload
    except Exception as exc:
        fail_task_run(task_run, str(exc), session=session)
        raise
    finally:
        session.close()


@celery_app.task(name="ingestion.sync_instrument_universe")
def sync_instrument_universe_task(
    market: str = "CN",
    provider: str = "akshare",
    asset_type: str = "stock",
    task_run_id: str | None = None,
) -> dict[str, object]:
    normalized_market = market.strip().upper()
    normalized_provider = provider.strip().lower()
    normalized_asset_type = asset_type.strip().lower()
    session = SessionLocal()

    if task_run_id:
        task_run = session.get(TaskRun, UUID(task_run_id))
        if task_run is None:
            session.close()
            msg = f"Task run not found: {task_run_id}"
            raise ValueError(msg)
    else:
        task_run = start_task_run(
            "ingestion.sync_instrument_universe",
            {
                "market": normalized_market,
                "provider": normalized_provider,
                "asset_type": normalized_asset_type,
            },
            session=session,
        )

    try:
        update_task_run_progress(
            task_run,
            phase="fetching",
            current=0,
            total=2,
            message="Fetching the provider instrument universe.",
            session=session,
        )
        result = sync_instrument_universe(
            session=session,
            market=normalized_market,
            provider_name=normalized_provider,
            asset_type=normalized_asset_type,
        )
        if result["status"] == "failed":
            msg = "Instrument universe refresh failed; the last good universe was preserved."
            raise RuntimeError(msg)
        result_payload = {
            **result,
            "progress": {
                "phase": "completed",
                "current": 2,
                "total": 2,
                "message": "Instrument universe synchronization completed.",
            },
        }
        finish_task_run(task_run, result_payload, session=session)
        return result_payload
    except Exception as exc:
        fail_task_run(task_run, str(exc), session=session)
        raise
    finally:
        session.close()


@celery_app.task(name=CN_FUND_INDEX_PIPELINE_TASK_NAME)
def sync_cn_fund_index_data_task(
    lookback_days: int | None = None,
    max_symbols_per_type: int | None = None,
    trigger: str = "manual",
    task_run_id: str | None = None,
) -> dict[str, object]:
    effective_lookback = (
        settings.cn_fund_index_pipeline_lookback_days
        if lookback_days is None
        else lookback_days
    )
    effective_limit = (
        settings.cn_fund_index_pipeline_max_symbols_per_type
        if max_symbols_per_type is None
        else max_symbols_per_type
    )
    if not 7 <= effective_lookback <= 730:
        raise ValueError("CN fund/index lookback days must be between 7 and 730.")
    if not 1 <= effective_limit <= 5_000:
        raise ValueError("CN fund/index symbol limit must be between 1 and 5000.")

    end_date = datetime.now(ZoneInfo("Asia/Shanghai")).date()
    start_date = end_date - timedelta(days=effective_lookback)
    session = SessionLocal()
    task_run = None
    try:
        if task_run_id:
            task_run = session.get(TaskRun, UUID(task_run_id))
            if task_run is None:
                raise ValueError("Invalid task run identity.")
        else:
            cutoff = datetime.now(ZoneInfo("UTC")) - timedelta(
                minutes=settings.task_run_stale_minutes
            )
            active = (
                session.query(TaskRun)
                .filter(TaskRun.task_name == CN_FUND_INDEX_PIPELINE_TASK_NAME)
                .filter(TaskRun.status == "running")
                .filter(TaskRun.heartbeat_at >= cutoff)
                .first()
            )
            if active is not None:
                return {
                    "status": "skipped",
                    "provider": "akshare",
                    "pipeline": "cn_fund_index_data",
                    "code": "ALREADY_RUNNING",
                }
            task_run = start_task_run(
                CN_FUND_INDEX_PIPELINE_TASK_NAME,
                {
                    "provider": "akshare",
                    "pipeline": "cn_fund_index_data",
                    "asset_types": ["etf", "index"],
                    "lookback_days": effective_lookback,
                    "max_symbols_per_type": effective_limit,
                    "trigger": trigger,
                },
                session=session,
            )

        def report_progress(phase: str, current: int, total: int, message: str) -> None:
            update_task_run_progress(
                task_run,
                phase=phase,
                current=current,
                total=total,
                message=message,
                session=session,
            )

        result = sync_cn_fund_index_data(
            session=session,
            start=start_date,
            end=end_date,
            max_symbols_per_type=effective_limit,
            request_delay_seconds=max(
                0,
                settings.cn_fund_index_pipeline_request_delay_ms,
            )
            / 1000,
            progress_callback=report_progress,
        )
        finish_task_run(task_run, result, session=session)
        return result
    except Exception as error:
        session.rollback()
        if task_run is not None and task_run.status == "running":
            code = (
                error.code
                if isinstance(error, CnFundIndexPipelineError)
                else "CN_FUND_INDEX_PIPELINE_FAILED"
            )
            fail_task_run(task_run, code, session=session)
        raise
    finally:
        session.close()


@celery_app.task(name="ingestion.sync_corporate_actions")
def sync_corporate_actions_task(
    report_period: str,
    market: str = "CN",
    provider: str = "akshare",
    symbols: list[str] | None = None,
    event_types: list[str] | None = None,
    cursor: int = 0,
    batch_size: int = 50,
    task_run_id: str | None = None,
) -> dict[str, object]:
    normalized_market = market.strip().upper()
    normalized_provider = provider.strip().lower()
    normalized_symbols = sorted(
        {symbol.strip().upper() for symbol in symbols or [] if symbol.strip()}
    )
    normalized_event_types = event_types or ["dividend_bonus", "rights_allotment"]
    session = SessionLocal()

    if task_run_id:
        task_run = session.get(TaskRun, UUID(task_run_id))
        if task_run is None:
            session.close()
            msg = f"Task run not found: {task_run_id}"
            raise ValueError(msg)
    else:
        task_run = start_task_run(
            "ingestion.sync_corporate_actions",
            {
                "report_period": report_period,
                "market": normalized_market,
                "provider": normalized_provider,
                "symbols": normalized_symbols,
                "event_types": normalized_event_types,
                "cursor": cursor,
                "batch_size": batch_size,
            },
            session=session,
        )

    def report_progress(phase: str, current: int, total: int, message: str) -> None:
        update_task_run_progress(
            task_run,
            phase=phase,
            current=current,
            total=total,
            message=message,
            session=session,
        )

    try:
        result = sync_corporate_action_evidence(
            CorporateActionSyncInput(
                report_period=date.fromisoformat(report_period),
                market=normalized_market,
                provider_name=normalized_provider,
                symbols=tuple(normalized_symbols),
                event_types=tuple(normalized_event_types),
                cursor=cursor,
                batch_size=batch_size,
            ),
            session=session,
            progress_callback=report_progress,
        )
        if result["status"] == "failed":
            msg = "Corporate-action provider refresh failed for the requested batch."
            raise RuntimeError(msg)
        result_payload = {
            **result,
            "progress": {
                "phase": "completed",
                "current": len(normalized_event_types) + 1,
                "total": len(normalized_event_types) + 1,
                "message": "Corporate-action evidence batch completed.",
            },
        }
        finish_task_run(task_run, result_payload, session=session)
        return result_payload
    except Exception as exc:
        fail_task_run(task_run, str(exc), session=session)
        raise
    finally:
        session.close()


@celery_app.task(name="ingestion.ingest_symbol_daily_bars_batch")
def ingest_symbol_daily_bars_batch_task(
    symbols: str | list[str],
    market: str,
    start: str | None = None,
    end: str | None = None,
    provider: str | None = None,
    exchange: str | None = None,
    timeframe: str = "1d",
    asset_type: str = "stock",
    task_run_id: str | None = None,
) -> dict[str, object]:
    end_date = date.fromisoformat(end) if end else date.today()
    start_date = date.fromisoformat(start) if start else end_date - timedelta(days=2)
    normalized_market = market.strip().upper()
    session = SessionLocal()

    if task_run_id:
        task_run = session.get(TaskRun, UUID(task_run_id))
        if task_run is None:
            session.close()
            msg = f"Task run not found: {task_run_id}"
            raise ValueError(msg)
    else:
        try:
            task_input_symbols = normalize_symbol_list(symbols)
        except ValueError:
            task_input_symbols = []
        task_run = start_task_run(
            "ingestion.ingest_symbol_daily_bars_batch",
            {
                "symbols": task_input_symbols,
                "market": normalized_market,
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "provider": provider,
                "exchange": exchange,
                "timeframe": timeframe,
                "asset_type": asset_type,
            },
            session=session,
        )

    try:
        ingestion_result = ingest_symbol_daily_bars_batch(
            symbols=symbols,
            market=normalized_market,
            start=start_date,
            end=end_date,
            session=session,
            provider_name=provider,
            exchange=exchange,
            timeframe=timeframe,
            asset_type=asset_type,
        )
        result_payload = {
            "symbols": ingestion_result["symbols"],
            "market": str(ingestion_result["market"]),
            "asset_type": str(ingestion_result["asset_type"]),
            "symbol_count": int(ingestion_result["symbol_count"]),
            "succeeded_count": int(ingestion_result["succeeded_count"]),
            "no_data_count": int(ingestion_result["no_data_count"]),
            "failed_count": int(ingestion_result["failed_count"]),
            "total_bar_count": int(ingestion_result["total_bar_count"]),
            "status": str(ingestion_result["status"]),
            "provider": str(ingestion_result["provider"]),
            "requested_provider": ingestion_result.get("requested_provider"),
            "timeframe": str(ingestion_result["timeframe"]),
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "items": ingestion_result["items"],
            "diagnostics": ingestion_result["diagnostics"],
        }
        finish_task_run(task_run, result_payload, session=session)
        return result_payload
    except Exception as exc:
        fail_task_run(task_run, str(exc), session=session)
        raise
    finally:
        session.close()


@celery_app.task(name=WATCHLIST_DISCLOSURE_TASK_NAME)
def ingest_watchlist_official_disclosures_task(
    lookback_days: int = 30,
    max_documents: int = 20,
    mode: str = "batch",
    task_run_id: str | None = None,
) -> dict[str, object]:
    session = SessionLocal()
    if task_run_id:
        task_run = session.get(TaskRun, UUID(task_run_id))
        if task_run is None:
            session.close()
            raise ValueError(f"Task run not found: {task_run_id}")
    else:
        task_run = start_task_run(
            WATCHLIST_DISCLOSURE_TASK_NAME,
            {
                "lookback_days": lookback_days,
                "max_documents": max_documents,
                "mode": mode,
            },
            session=session,
        )

    def report_progress(phase: str, current: int, total: int, message: str) -> None:
        update_task_run_progress(
            task_run,
            phase=phase,
            current=current,
            total=total,
            message=message,
            session=session,
        )

    try:
        if mode == "incremental":
            result = ingest_watchlist_official_disclosures(
                session=session,
                lookback_days=lookback_days,
                max_documents=max_documents,
                mode=mode,
                overlap_days=settings.disclosure_monitor_overlap_days,
                retry_base_minutes=settings.disclosure_monitor_retry_base_minutes,
                retry_max_minutes=settings.disclosure_monitor_retry_max_minutes,
                task_run_id=str(task_run.id),
                request_delay_seconds=max(
                    0.25,
                    settings.disclosure_batch_request_delay_ms / 1000,
                ),
                progress_callback=report_progress,
            )
        else:
            result = ingest_watchlist_official_disclosures(
                session=session,
                lookback_days=lookback_days,
                max_documents=max_documents,
                request_delay_seconds=max(
                    0.25,
                    settings.disclosure_batch_request_delay_ms / 1000,
                ),
                progress_callback=report_progress,
            )
        finish_task_run(task_run, result, session=session)
        return result
    except Exception as exc:
        fail_task_run(task_run, str(exc), session=session)
        raise
    finally:
        session.close()


@celery_app.task(name=WATCHLIST_DISCLOSURE_SCHEDULE_TASK_NAME)
def schedule_watchlist_official_disclosures_task() -> dict[str, object]:
    session = SessionLocal()
    try:
        return enqueue_watchlist_official_disclosure_ingestion(
            session=session,
            lookback_days=settings.disclosure_monitor_lookback_days,
            max_documents=settings.disclosure_monitor_max_documents,
            mode="incremental",
        )
    finally:
        session.close()


@celery_app.task(name=BACKFILL_TASK_NAME)
def backfill_a_share_research_evidence_task(
    backfill_run_id: str,
    task_run_id: str | None = None,
) -> dict[str, object]:
    session = SessionLocal()
    if task_run_id:
        task_run = session.get(TaskRun, UUID(task_run_id))
        if task_run is None:
            session.close()
            raise ValueError(f"Task run not found: {task_run_id}")
    else:
        task_run = start_task_run(
            BACKFILL_TASK_NAME,
            {"backfill_run_id": backfill_run_id},
            session=session,
        )

    try:
        link_backfill_task_run(backfill_run_id, str(task_run.id), session=session)

        def report_progress(phase: str, current: int, total: int, message: str) -> None:
            update_task_run_progress(
                task_run,
                phase=phase,
                current=current,
                total=total,
                message=message,
                session=session,
            )

        result = execute_backfill_run(
            backfill_run_id,
            session=session,
            progress_callback=report_progress,
            request_delay_seconds=max(
                0.0,
                settings.a_share_backfill_request_delay_ms / 1000,
            ),
            max_transient_attempts=settings.a_share_backfill_max_transient_attempts,
            retry_base_seconds=settings.a_share_backfill_retry_base_seconds,
        )
        finish_task_run(task_run, result, session=session)
        return result
    except Exception as exc:
        try:
            fail_backfill_run(backfill_run_id, session=session)
        finally:
            fail_task_run(task_run, str(exc), session=session)
        raise
    finally:
        session.close()


@celery_app.task(name="ingestion.schedule_a_share_evidence_backfill")
def schedule_a_share_evidence_backfill_task(
    run_kind: str,
    evidence_kinds: list[str],
    shard_index: int | None = None,
    shard_count: int | None = None,
    daily_bar_policy: str = STRICT_POLICY,
) -> dict[str, object]:
    session = SessionLocal()
    try:
        if run_kind == "fundamental_shard" and shard_index is None:
            local_date = datetime.now(ZoneInfo("Asia/Shanghai")).date()
            shard_index = local_date.toordinal() % (shard_count or 5)
        created = create_backfill_run(
            BackfillRequest(
                run_kind=run_kind,
                evidence_kinds=tuple(evidence_kinds),
                shard_index=shard_index,
                shard_count=shard_count,
                daily_bar_policy=daily_bar_policy,
            ),
            session=session,
        )
        if created["status"] != "created":
            return created
        item = created["item"]
        if not isinstance(item, dict):
            raise RuntimeError("Created scheduled backfill payload is invalid.")
        dispatched = enqueue_task_run(
            BACKFILL_TASK_NAME,
            {
                "backfill_run_id": item["id"],
                "market": item["market"],
                "provider": item["provider"],
                "run_kind": item["run_kind"],
            },
            session=session,
        )
        task_run = dispatched.get("task_run")
        if isinstance(task_run, dict) and task_run.get("id"):
            link_backfill_task_run(str(item["id"]), str(task_run["id"]), session=session)
        if dispatched["status"] != "dispatched":
            fail_backfill_run(
                str(item["id"]),
                session=session,
                code="BACKFILL_DISPATCH_FAILED",
            )
        return {**dispatched, "backfill": item}
    finally:
        session.close()
