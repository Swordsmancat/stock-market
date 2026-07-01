"""Verify Celery worker can connect to Redis and dispatch a task."""

from __future__ import annotations

import sys

from packages.shared.config import settings


def main() -> int:
    try:
        from apps.worker.celery_app import celery_app
        import apps.worker.tasks.ingestion  # noqa: F401
        import apps.worker.tasks.reports  # noqa: F401
        import apps.worker.tasks.alerts  # noqa: F401
    except Exception as exc:
        print(f"FAIL: cannot import celery app: {exc}")
        return 1

    try:
        conn = celery_app.connection()
        conn.ensure_connection(max_retries=3)
    except Exception as exc:
        print(f"FAIL: cannot connect to Redis at {settings.redis_url}: {exc}")
        return 1

    registered = sorted(celery_app.tasks.keys())
    expected = {
        "ingestion.ingest_market_data",
        "reports.refresh_daily_stock_analysis",
        "reports.refresh_daily_watchlist_analysis",
        "alerts.evaluate_watchlist_alerts",
    }
    missing = expected - set(registered)
    if missing:
        print(f"FAIL: missing registered tasks: {sorted(missing)}")
        return 1

    print(f"OK: Celery connected to {settings.redis_url}")
    print(f"OK: {len(registered)} tasks registered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
