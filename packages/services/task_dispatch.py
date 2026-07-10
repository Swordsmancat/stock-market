from collections.abc import Callable
from typing import Any


def _dispatch_watchlist_analysis(input_json: dict[str, Any], task_run_id: str) -> str:
    from apps.worker.tasks.reports import refresh_daily_watchlist_analysis

    async_result = refresh_daily_watchlist_analysis.delay(
        watchlist=input_json.get("watchlist"),
        start=input_json.get("start"),
        end=input_json.get("end"),
        ma_window=input_json.get("ma_window"),
        provider=input_json.get("provider"),
        task_run_id=task_run_id,
    )
    return async_result.id


def _dispatch_stock_analysis(input_json: dict[str, Any], task_run_id: str) -> str:
    from apps.worker.tasks.reports import refresh_daily_stock_analysis

    async_result = refresh_daily_stock_analysis.delay(
        symbol=input_json["symbol"],
        market=input_json["market"],
        start=input_json.get("start"),
        end=input_json.get("end"),
        ma_window=input_json.get("ma_window", 20),
        provider=input_json.get("provider"),
        task_run_id=task_run_id,
    )
    return async_result.id


def _dispatch_market_ingestion(input_json: dict[str, Any], task_run_id: str) -> str:
    from apps.worker.tasks.ingestion import ingest_market_data

    async_result = ingest_market_data.delay(
        market=input_json["market"],
        start=input_json.get("start"),
        end=input_json.get("end"),
        provider=input_json.get("provider"),
        task_run_id=task_run_id,
    )
    return async_result.id


def _dispatch_instrument_universe_sync(input_json: dict[str, Any], task_run_id: str) -> str:
    from apps.worker.tasks.ingestion import sync_instrument_universe_task

    async_result = sync_instrument_universe_task.delay(
        market=input_json.get("market", "CN"),
        provider=input_json.get("provider", "akshare"),
        task_run_id=task_run_id,
    )
    return async_result.id


def _dispatch_corporate_action_sync(input_json: dict[str, Any], task_run_id: str) -> str:
    from apps.worker.tasks.ingestion import sync_corporate_actions_task

    async_result = sync_corporate_actions_task.delay(
        report_period=input_json["report_period"],
        market=input_json.get("market", "CN"),
        provider=input_json.get("provider", "akshare"),
        symbols=input_json.get("symbols"),
        event_types=input_json.get("event_types"),
        cursor=input_json.get("cursor", 0),
        batch_size=input_json.get("batch_size", 50),
        task_run_id=task_run_id,
    )
    return async_result.id


def _dispatch_symbol_daily_bars_ingestion(input_json: dict[str, Any], task_run_id: str) -> str:
    from apps.worker.tasks.ingestion import ingest_symbol_daily_bars_task

    async_result = ingest_symbol_daily_bars_task.delay(
        symbol=input_json["symbol"],
        market=input_json["market"],
        start=input_json.get("start"),
        end=input_json.get("end"),
        provider=input_json.get("provider"),
        exchange=input_json.get("exchange"),
        timeframe=input_json.get("timeframe", "1d"),
        asset_type=input_json.get("asset_type", "stock"),
        task_run_id=task_run_id,
    )
    return async_result.id


def _dispatch_symbol_daily_bars_batch_ingestion(
    input_json: dict[str, Any],
    task_run_id: str,
) -> str:
    from apps.worker.tasks.ingestion import ingest_symbol_daily_bars_batch_task

    async_result = ingest_symbol_daily_bars_batch_task.delay(
        symbols=input_json["symbols"],
        market=input_json["market"],
        start=input_json.get("start"),
        end=input_json.get("end"),
        provider=input_json.get("provider"),
        exchange=input_json.get("exchange"),
        timeframe=input_json.get("timeframe", "1d"),
        asset_type=input_json.get("asset_type", "stock"),
        task_run_id=task_run_id,
    )
    return async_result.id


def _dispatch_research_evidence_backfill(
    input_json: dict[str, Any],
    task_run_id: str,
) -> str:
    from apps.worker.tasks.ingestion import backfill_a_share_research_evidence_task

    async_result = backfill_a_share_research_evidence_task.delay(
        backfill_run_id=input_json["backfill_run_id"],
        task_run_id=task_run_id,
    )
    return async_result.id


def _dispatch_alert_evaluation(input_json: dict[str, Any], task_run_id: str) -> str:
    from apps.worker.tasks.alerts import evaluate_watchlist_alerts

    async_result = evaluate_watchlist_alerts.delay(
        provider=input_json.get("provider"),
        task_run_id=task_run_id,
    )
    return async_result.id


_DISPATCHERS: dict[str, Callable[[dict[str, Any], str], str]] = {
    "reports.refresh_daily_watchlist_analysis": _dispatch_watchlist_analysis,
    "reports.refresh_daily_stock_analysis": _dispatch_stock_analysis,
    "ingestion.ingest_market_data": _dispatch_market_ingestion,
    "ingestion.sync_instrument_universe": _dispatch_instrument_universe_sync,
    "ingestion.sync_corporate_actions": _dispatch_corporate_action_sync,
    "ingestion.ingest_symbol_daily_bars": _dispatch_symbol_daily_bars_ingestion,
    "ingestion.ingest_symbol_daily_bars_batch": _dispatch_symbol_daily_bars_batch_ingestion,
    "ingestion.backfill_a_share_research_evidence": _dispatch_research_evidence_backfill,
    "alerts.evaluate_watchlist_alerts": _dispatch_alert_evaluation,
}


def dispatch_task_run(task_name: str, input_json: dict[str, Any], task_run_id: str) -> str:
    dispatcher = _DISPATCHERS.get(task_name)
    if dispatcher is None:
        msg = f"Unsupported task for Celery dispatch: {task_name}"
        raise ValueError(msg)
    return dispatcher(input_json, task_run_id)


def is_dispatchable_task(task_name: str) -> bool:
    return task_name in _DISPATCHERS
