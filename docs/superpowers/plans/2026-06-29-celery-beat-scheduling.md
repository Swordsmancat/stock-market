# Celery Beat Daily Report Scheduling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing daily stock analysis worker run on a repeatable Celery Beat schedule and document how to run worker/beat locally.

**Architecture:** Keep the scheduling configuration inside `apps/worker/celery_app.py`, driven by typed settings from `packages/shared/config.py`. Reuse the existing `reports.refresh_daily_stock_analysis` Celery task so the scheduled path follows the same analysis pipeline as manual refreshes.

**Tech Stack:** Python, Celery, Redis, Pydantic Settings, Docker Compose, pytest, Ruff.

---

### Task 1: Configure Celery Beat schedule

**Files:**
- Modify: `packages/shared/config.py`
- Modify: `apps/worker/celery_app.py`
- Test: `tests/worker/test_celery_schedule.py`

- [ ] **Step 1: Write the failing schedule test**

Create `tests/worker/test_celery_schedule.py` with:

```python
from apps.worker.celery_app import celery_app


def test_celery_beat_schedules_daily_stock_analysis_report():
    schedule = celery_app.conf.beat_schedule["daily-stock-analysis-report"]

    assert schedule["task"] == "reports.refresh_daily_stock_analysis"
    assert schedule["kwargs"] == {
        "symbol": "AAPL",
        "market": "US",
        "start": "2026-01-01",
        "end": "2026-01-20",
        "ma_window": 3,
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/worker/test_celery_schedule.py -v`

Expected: FAIL because `daily-stock-analysis-report` is not in `celery_app.conf.beat_schedule`.

- [ ] **Step 3: Add settings and beat schedule**

In `packages/shared/config.py`, add these fields to `Settings`:

```python
daily_report_symbol: str = "AAPL"
daily_report_market: str = "US"
daily_report_start: str = "2026-01-01"
daily_report_end: str = "2026-01-20"
daily_report_ma_window: int = 3
daily_report_cron_hour: int = 21
daily_report_cron_minute: int = 30
```

In `apps/worker/celery_app.py`, configure beat:

```python
from celery import Celery
from celery.schedules import crontab

from packages.shared.config import settings

celery_app = Celery(
    "stock_analysis_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.beat_schedule = {
    "daily-stock-analysis-report": {
        "task": "reports.refresh_daily_stock_analysis",
        "schedule": crontab(
            hour=settings.daily_report_cron_hour,
            minute=settings.daily_report_cron_minute,
        ),
        "kwargs": {
            "symbol": settings.daily_report_symbol,
            "market": settings.daily_report_market,
            "start": settings.daily_report_start,
            "end": settings.daily_report_end,
            "ma_window": settings.daily_report_ma_window,
        },
    }
}
celery_app.autodiscover_tasks(["apps.worker.tasks"])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/worker/test_celery_schedule.py -v`

Expected: PASS.

### Task 2: Document local worker and beat execution

**Files:**
- Modify: `docker-compose.yml`
- Modify: `docs/runbooks/local-development.md`

- [ ] **Step 1: Add worker and beat services**

Add `worker` and `beat` services to `docker-compose.yml` using `python:3.13-slim`, mounting the repository at `/app`, installing the editable project, and running Celery worker/beat against the existing `db` and `redis` services.

- [ ] **Step 2: Update local runbook**

Add commands for:

```bash
celery -A apps.worker.celery_app.celery_app worker --loglevel=info
celery -A apps.worker.celery_app.celery_app beat --loglevel=info
docker compose up -d db redis worker beat
```

### Task 3: Verify the scheduling closure

**Files:**
- Test: `tests/worker/test_celery_schedule.py`
- Test: `tests/worker/test_tasks.py`
- Test: `tests/api/test_reports_api.py`
- Test: `apps/web/app/page.test.tsx`

- [ ] **Step 1: Run targeted backend tests**

Run: `python -m pytest tests/worker/test_celery_schedule.py tests/worker/test_tasks.py tests/api/test_reports_api.py -v`

Expected: PASS.

- [ ] **Step 2: Run frontend test**

Run: `npm run test:web`

Expected: PASS.

- [ ] **Step 3: Run Ruff**

Run: `python -m ruff check packages/shared/config.py apps/worker/celery_app.py apps/worker/tasks/reports.py tests/worker/test_celery_schedule.py tests/worker/test_tasks.py tests/api/test_reports_api.py`

Expected: `All checks passed!`.
