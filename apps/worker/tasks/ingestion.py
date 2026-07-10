from datetime import date, timedelta
from uuid import UUID

from apps.worker.celery_app import celery_app
from packages.domain.models import TaskRun
from packages.services.corporate_actions import (
    CorporateActionSyncInput,
    sync_corporate_action_evidence,
)
from packages.services.ingestion import (
    ingest_market_snapshot,
    ingest_symbol_daily_bars,
    ingest_symbol_daily_bars_batch,
    normalize_symbol_list,
)
from packages.services.instrument_universe import sync_instrument_universe
from packages.services.task_runs import (
    fail_task_run,
    finish_task_run,
    start_task_run,
    update_task_run_progress,
)
from packages.shared.config import settings
from packages.shared.database import SessionLocal


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
    task_run_id: str | None = None,
) -> dict[str, object]:
    normalized_market = market.strip().upper()
    normalized_provider = provider.strip().lower()
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
            {"market": normalized_market, "provider": normalized_provider},
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
