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


def _dispatch_watchlist_official_disclosures(
    input_json: dict[str, Any],
    task_run_id: str,
) -> str:
    from apps.worker.tasks.ingestion import ingest_watchlist_official_disclosures_task

    kwargs = {
        "lookback_days": input_json.get("lookback_days", 30),
        "max_documents": input_json.get("max_documents", 20),
        "task_run_id": task_run_id,
    }
    if "mode" in input_json:
        kwargs["mode"] = input_json["mode"]
    async_result = ingest_watchlist_official_disclosures_task.delay(**kwargs)
    return async_result.id


def _dispatch_daily_research_loop(
    input_json: dict[str, Any],
    task_run_id: str,
) -> str:
    from apps.worker.tasks.research import run_daily_research_loop_task

    async_result = run_daily_research_loop_task.delay(
        market=input_json.get("market", "CN"),
        asset_type=input_json.get("asset_type", "stock"),
        profile_id=input_json.get("profile_id", "balanced_research"),
        shortlist_limit=input_json.get("shortlist_limit", 10),
        locale=input_json.get("locale", "zh"),
        use_llm=input_json.get("use_llm", True),
        outcome_run_limit=input_json.get("outcome_run_limit"),
        trigger=input_json.get("trigger", "manual"),
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


def _dispatch_eastmoney_task(input_json: dict[str, Any], task_run_id: str) -> str:
    from apps.worker.tasks import ingestion

    task_name = str(input_json["task_name"])
    tasks = {
        "ingestion.refresh_eastmoney_economic_calendar": (
            ingestion.refresh_eastmoney_economic_calendar_task
        ),
        "ingestion.refresh_eastmoney_industry_rankings": (
            ingestion.refresh_eastmoney_industry_rankings_task
        ),
        "ingestion.refresh_eastmoney_research_news": (
            ingestion.refresh_eastmoney_research_news_task
        ),
        "ingestion.refresh_eastmoney_research_fundamentals": (
            ingestion.refresh_eastmoney_research_fundamentals_task
        ),
    }
    async_result = tasks[task_name].delay(
        trigger=input_json.get("trigger", "manual"),
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
    "ingestion.ingest_watchlist_official_disclosures": _dispatch_watchlist_official_disclosures,
    "research.run_daily_research_loop": _dispatch_daily_research_loop,
    "alerts.evaluate_watchlist_alerts": _dispatch_alert_evaluation,
}

for _eastmoney_task_name in (
    "ingestion.refresh_eastmoney_economic_calendar",
    "ingestion.refresh_eastmoney_industry_rankings",
    "ingestion.refresh_eastmoney_research_news",
    "ingestion.refresh_eastmoney_research_fundamentals",
):
    _DISPATCHERS[_eastmoney_task_name] = (
        lambda input_json, task_run_id, task_name=_eastmoney_task_name: _dispatch_eastmoney_task(
            {**input_json, "task_name": task_name}, task_run_id
        )
    )


def dispatch_task_run(task_name: str, input_json: dict[str, Any], task_run_id: str) -> str:
    dispatcher = _DISPATCHERS.get(task_name)
    if dispatcher is None:
        msg = f"Unsupported task for Celery dispatch: {task_name}"
        raise ValueError(msg)
    return dispatcher(input_json, task_run_id)


def is_dispatchable_task(task_name: str) -> bool:
    return task_name in _DISPATCHERS
