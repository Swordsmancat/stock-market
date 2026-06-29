from datetime import date

from apps.worker.celery_app import celery_app
from packages.services.analysis import refresh_stock_analysis
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
        return {"status": "refreshed", "item_count": len(items), "items": items}
    finally:
        session.close()
