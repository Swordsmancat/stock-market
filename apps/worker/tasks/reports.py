from datetime import date
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from apps.worker.celery_app import celery_app
from packages.domain.models import TaskRun
from packages.services.analysis import refresh_stock_analysis
from packages.services.task_runs import fail_task_run, finish_task_run, start_task_run
from packages.services.watchlists import format_watchlist_entries, get_active_watchlist_entries
from packages.shared.config import settings
from packages.shared.database import SessionLocal
from packages.shared.dates import date_range_ending_today


@celery_app.task(name="reports.generate_daily_reports")
def generate_daily_reports(scope: str) -> dict[str, str]:
    return {"scope": scope, "status": "scheduled"}


@celery_app.task(name="reports.refresh_daily_stock_analysis")
def refresh_daily_stock_analysis(
    symbol: str,
    market: str,
    start: str | None = None,
    end: str | None = None,
    ma_window: int = 20,
    provider: str | None = None,
    task_run_id: str | None = None,
) -> dict[str, object]:
    default_start, default_end = date_range_ending_today(20)
    start_value = start or default_start
    end_value = end or default_end
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
            "reports.refresh_daily_stock_analysis",
            {
                "symbol": symbol,
                "market": market,
                "start": start_value,
                "end": end_value,
                "ma_window": ma_window,
                "provider": provider_value,
            },
            session=session,
        )

    try:
        result = refresh_stock_analysis(
            symbol=symbol,
            market=market,
            start=date.fromisoformat(start_value),
            end=date.fromisoformat(end_value),
            session=session,
            ma_window=ma_window,
            provider_name=provider_value,
            task_run_id=task_run.id,
        )
        finish_task_run(task_run, result, session=session)
        return result
    except Exception as exc:
        fail_task_run(task_run, str(exc), session=session)
        raise
    finally:
        session.close()


def _parse_watchlist(watchlist: str) -> list[tuple[str, str]]:
    items = []
    for entry in watchlist.split(","):
        value = entry.strip()
        if not value:
            continue
        symbol, market = value.split(":", 1)
        items.append((symbol.strip(), market.strip()))
    return items


def _default_watchlist_value(session) -> str:
    try:
        entries = get_active_watchlist_entries(session)
    except SQLAlchemyError:
        session.rollback()
        return settings.daily_report_watchlist
    if not entries:
        return settings.daily_report_watchlist
    return format_watchlist_entries(entries)


@celery_app.task(name="reports.refresh_daily_watchlist_analysis")
def refresh_daily_watchlist_analysis(
    watchlist: str | None = None,
    start: str | None = None,
    end: str | None = None,
    ma_window: int | None = None,
    provider: str | None = None,
    task_run_id: str | None = None,
) -> dict[str, object]:
    session = SessionLocal()
    default_start, default_end = date_range_ending_today(20)
    start_value = start or default_start
    end_value = end or default_end
    ma_window_value = ma_window or settings.daily_report_ma_window
    provider_value = provider or settings.market_data_provider
    watchlist_value = watchlist or _default_watchlist_value(session)

    if task_run_id:
        task_run = session.get(TaskRun, UUID(task_run_id))
        if task_run is None:
            session.close()
            msg = f"Task run not found: {task_run_id}"
            raise ValueError(msg)
    else:
        task_run = start_task_run(
            "reports.refresh_daily_watchlist_analysis",
            {
                "watchlist": watchlist_value,
                "start": start_value,
                "end": end_value,
                "ma_window": ma_window_value,
                "provider": provider_value,
            },
            session=session,
        )

    try:
        items = []
        for symbol, market in _parse_watchlist(watchlist_value):
            result = refresh_stock_analysis(
                symbol=symbol,
                market=market,
                start=date.fromisoformat(start_value),
                end=date.fromisoformat(end_value),
                session=session,
                ma_window=ma_window_value,
                provider_name=provider_value,
                task_run_id=task_run.id,
            )
            items.append(
                {
                    "symbol": symbol,
                    "market": market,
                    "status": result["status"],
                    "report": result["report"],
                }
            )
        result_payload = {"status": "refreshed", "item_count": len(items), "items": items}
        finish_task_run(task_run, result_payload, session=session)
        return result_payload
    except Exception as exc:
        fail_task_run(task_run, str(exc), session=session)
        raise
    finally:
        session.close()
