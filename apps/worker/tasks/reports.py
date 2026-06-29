from datetime import date

from apps.worker.celery_app import celery_app
from packages.services.analysis import refresh_stock_analysis
from packages.services.task_runs import fail_task_run, finish_task_run, start_task_run
from packages.shared.config import settings
from packages.shared.database import SessionLocal


@celery_app.task(name="reports.generate_daily_reports")
def generate_daily_reports(scope: str) -> dict[str, str]:
    return {"scope": scope, "status": "scheduled"}


@celery_app.task(name="reports.refresh_daily_stock_analysis")
def refresh_daily_stock_analysis(
    symbol: str,
    market: str,
    start: str,
    end: str,
    ma_window: int = 20,
) -> dict[str, object]:
    session = SessionLocal()
    try:
        return refresh_stock_analysis(
            symbol=symbol,
            market=market,
            start=date.fromisoformat(start),
            end=date.fromisoformat(end),
            session=session,
            ma_window=ma_window,
        )
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


@celery_app.task(name="reports.refresh_daily_watchlist_analysis")
def refresh_daily_watchlist_analysis(
    watchlist: str | None = None,
    start: str | None = None,
    end: str | None = None,
    ma_window: int | None = None,
) -> dict[str, object]:
    session = SessionLocal()
    start_value = start or settings.daily_report_start
    end_value = end or settings.daily_report_end
    ma_window_value = ma_window or settings.daily_report_ma_window
    watchlist_value = watchlist or settings.daily_report_watchlist
    task_run = start_task_run(
        "reports.refresh_daily_watchlist_analysis",
        {
            "watchlist": watchlist_value,
            "start": start_value,
            "end": end_value,
            "ma_window": ma_window_value,
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
