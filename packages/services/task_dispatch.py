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


_DISPATCHERS: dict[str, Callable[[dict[str, Any], str], str]] = {
    "reports.refresh_daily_watchlist_analysis": _dispatch_watchlist_analysis,
    "reports.refresh_daily_stock_analysis": _dispatch_stock_analysis,
    "ingestion.ingest_market_data": _dispatch_market_ingestion,
}


def dispatch_task_run(task_name: str, input_json: dict[str, Any], task_run_id: str) -> str:
    dispatcher = _DISPATCHERS.get(task_name)
    if dispatcher is None:
        msg = f"Unsupported task for Celery dispatch: {task_name}"
        raise ValueError(msg)
    return dispatcher(input_json, task_run_id)


def is_dispatchable_task(task_name: str) -> bool:
    return task_name in _DISPATCHERS
