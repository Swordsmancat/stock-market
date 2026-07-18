"""Run Celery-backed task runs synchronously in tests."""

from typing import Any

from sqlalchemy.orm import Session


def _run_with_session(session: Session, runner) -> str:
    from apps.worker.tasks import ingestion as ingestion_tasks
    from apps.worker.tasks import reports as report_tasks
    from apps.worker.tasks import research as research_tasks

    original_report_session = report_tasks.SessionLocal
    original_ingestion_session = ingestion_tasks.SessionLocal
    original_research_session = research_tasks.SessionLocal
    report_tasks.SessionLocal = lambda: session
    ingestion_tasks.SessionLocal = lambda: session
    research_tasks.SessionLocal = lambda: session
    try:
        runner()
    finally:
        report_tasks.SessionLocal = original_report_session
        ingestion_tasks.SessionLocal = original_ingestion_session
        research_tasks.SessionLocal = original_research_session
    session.expire_all()
    return "sync-celery-id"


def dispatch_task_run_sync(
    task_name: str,
    input_json: dict[str, Any],
    task_run_id: str,
    session: Session,
) -> str:
    if task_name == "reports.refresh_daily_watchlist_analysis":
        from apps.worker.tasks.reports import refresh_daily_watchlist_analysis

        return _run_with_session(
            session,
            lambda: refresh_daily_watchlist_analysis.run(
                watchlist=input_json.get("watchlist"),
                start=input_json.get("start"),
                end=input_json.get("end"),
                ma_window=input_json.get("ma_window"),
                provider=input_json.get("provider"),
                task_run_id=task_run_id,
            ),
        )

    if task_name == "reports.refresh_daily_stock_analysis":
        from apps.worker.tasks.reports import refresh_daily_stock_analysis

        return _run_with_session(
            session,
            lambda: refresh_daily_stock_analysis.run(
                symbol=input_json["symbol"],
                market=input_json["market"],
                start=input_json.get("start"),
                end=input_json.get("end"),
                ma_window=input_json.get("ma_window", 20),
                provider=input_json.get("provider"),
                task_run_id=task_run_id,
            ),
        )

    if task_name == "ingestion.ingest_market_data":
        from apps.worker.tasks.ingestion import ingest_market_data

        return _run_with_session(
            session,
            lambda: ingest_market_data.run(
                market=input_json["market"],
                start=input_json.get("start"),
                end=input_json.get("end"),
                provider=input_json.get("provider"),
                task_run_id=task_run_id,
            ),
        )

    if task_name == "ingestion.sync_instrument_universe":
        from apps.worker.tasks.ingestion import sync_instrument_universe_task

        return _run_with_session(
            session,
            lambda: sync_instrument_universe_task.run(
                market=input_json.get("market", "CN"),
                provider=input_json.get("provider", "akshare"),
                asset_type=input_json.get("asset_type", "stock"),
                task_run_id=task_run_id,
            ),
        )

    if task_name == "ingestion.sync_cn_fund_index_data":
        from apps.worker.tasks.ingestion import sync_cn_fund_index_data_task

        return _run_with_session(
            session,
            lambda: sync_cn_fund_index_data_task.run(
                lookback_days=input_json.get("lookback_days"),
                max_symbols_per_type=input_json.get("max_symbols_per_type"),
                trigger=input_json.get("trigger", "manual"),
                task_run_id=task_run_id,
            ),
        )

    if task_name == "ingestion.sync_corporate_actions":
        from apps.worker.tasks.ingestion import sync_corporate_actions_task

        return _run_with_session(
            session,
            lambda: sync_corporate_actions_task.run(
                report_period=input_json["report_period"],
                market=input_json.get("market", "CN"),
                provider=input_json.get("provider", "akshare"),
                symbols=input_json.get("symbols"),
                event_types=input_json.get("event_types"),
                cursor=input_json.get("cursor", 0),
                batch_size=input_json.get("batch_size", 50),
                task_run_id=task_run_id,
            ),
        )

    if task_name == "ingestion.ingest_symbol_daily_bars":
        from apps.worker.tasks.ingestion import ingest_symbol_daily_bars_task

        return _run_with_session(
            session,
            lambda: ingest_symbol_daily_bars_task.run(
                symbol=input_json["symbol"],
                market=input_json["market"],
                start=input_json.get("start"),
                end=input_json.get("end"),
                provider=input_json.get("provider"),
                exchange=input_json.get("exchange"),
                timeframe=input_json.get("timeframe", "1d"),
                asset_type=input_json.get("asset_type", "stock"),
                task_run_id=task_run_id,
            ),
        )

    if task_name == "ingestion.ingest_symbol_daily_bars_batch":
        from apps.worker.tasks.ingestion import ingest_symbol_daily_bars_batch_task

        return _run_with_session(
            session,
            lambda: ingest_symbol_daily_bars_batch_task.run(
                symbols=input_json["symbols"],
                market=input_json["market"],
                start=input_json.get("start"),
                end=input_json.get("end"),
                provider=input_json.get("provider"),
                exchange=input_json.get("exchange"),
                timeframe=input_json.get("timeframe", "1d"),
                asset_type=input_json.get("asset_type", "stock"),
                task_run_id=task_run_id,
            ),
        )

    if task_name == "ingestion.backfill_a_share_research_evidence":
        from apps.worker.tasks.ingestion import backfill_a_share_research_evidence_task

        return _run_with_session(
            session,
            lambda: backfill_a_share_research_evidence_task.run(
                backfill_run_id=input_json["backfill_run_id"],
                task_run_id=task_run_id,
            ),
        )

    if task_name == "research.run_daily_research_loop":
        from apps.worker.tasks.research import run_daily_research_loop_task

        return _run_with_session(
            session,
            lambda: run_daily_research_loop_task.run(
                market=input_json.get("market", "CN"),
                asset_type=input_json.get("asset_type", "stock"),
                profile_id=input_json.get("profile_id", "balanced_research"),
                shortlist_limit=input_json.get("shortlist_limit", 10),
                locale=input_json.get("locale", "zh"),
                use_llm=input_json.get("use_llm", True),
                outcome_run_limit=input_json.get("outcome_run_limit"),
                trigger=input_json.get("trigger", "manual"),
                task_run_id=task_run_id,
            ),
        )

    msg = f"Unsupported task for sync dispatch: {task_name}"
    raise ValueError(msg)
