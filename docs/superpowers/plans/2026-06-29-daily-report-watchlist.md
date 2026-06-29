# Daily Report Watchlist Scheduling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the scheduled daily report flow from a single hard-coded stock to a configurable watchlist that can refresh daily reports for multiple symbols.

**Architecture:** Keep the existing single-symbol Celery task for manual and targeted runs. Add a watchlist Celery task that parses `SYMBOL:MARKET` entries from settings, loops through the list, and reuses `refresh_stock_analysis` so each symbol follows the same ingestion, indicator, news, and report persistence pipeline.

**Tech Stack:** Python, Celery, Redis, Pydantic Settings, SQLAlchemy, pytest, Ruff, Docker Compose.

---

### Task 1: Add watchlist schedule contract

**Files:**
- Modify: `tests/worker/test_celery_schedule.py`

- [ ] **Step 1: Write the failing schedule test**

Replace `tests/worker/test_celery_schedule.py` with:

```python
from apps.worker.celery_app import celery_app


def test_celery_beat_schedules_daily_watchlist_analysis_report():
    schedule = celery_app.conf.beat_schedule["daily-watchlist-analysis-report"]

    assert schedule["task"] == "reports.refresh_daily_watchlist_analysis"
    assert schedule["kwargs"] == {
        "watchlist": "AAPL:US",
        "start": "2026-01-01",
        "end": "2026-01-20",
        "ma_window": 3,
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/worker/test_celery_schedule.py -v`

Expected: FAIL because `daily-watchlist-analysis-report` is not registered yet.

### Task 2: Implement configurable watchlist scheduling

**Files:**
- Modify: `packages/shared/config.py`
- Modify: `apps/worker/celery_app.py`

- [ ] **Step 1: Add settings**

Add this field to `Settings` in `packages/shared/config.py`:

```python
daily_report_watchlist: str = "AAPL:US"
```

- [ ] **Step 2: Update Celery Beat schedule**

Change `apps/worker/celery_app.py` so `celery_app.conf.beat_schedule` contains:

```python
celery_app.conf.beat_schedule = {
    "daily-watchlist-analysis-report": {
        "task": "reports.refresh_daily_watchlist_analysis",
        "schedule": crontab(
            hour=settings.daily_report_cron_hour,
            minute=settings.daily_report_cron_minute,
        ),
        "kwargs": {
            "watchlist": settings.daily_report_watchlist,
            "start": settings.daily_report_start,
            "end": settings.daily_report_end,
            "ma_window": settings.daily_report_ma_window,
        },
    }
}
```

- [ ] **Step 3: Run schedule test**

Run: `python -m pytest tests/worker/test_celery_schedule.py -v`

Expected: PASS.

### Task 3: Add watchlist worker task

**Files:**
- Modify: `apps/worker/tasks/reports.py`
- Modify: `tests/worker/test_tasks.py`

- [ ] **Step 1: Write the failing worker behavior test**

Add this test to `tests/worker/test_tasks.py`:

```python
def test_refresh_daily_watchlist_analysis_task_stores_reports_for_each_symbol(monkeypatch):
    session = make_session()
    monkeypatch.setattr(report_tasks, "SessionLocal", lambda: session)

    result = report_tasks.refresh_daily_watchlist_analysis(
        watchlist="AAPL:US,0700:HK",
        start="2026-01-01",
        end="2026-01-20",
        ma_window=3,
    )
    aapl_latest = get_latest_daily_report_payload("AAPL", session=session)
    hk_latest = get_latest_daily_report_payload("0700", session=session)

    assert result["status"] == "refreshed"
    assert result["item_count"] == 2
    assert [item["symbol"] for item in result["items"]] == ["AAPL", "0700"]
    assert aapl_latest["as_of"] == date(2026, 1, 20).isoformat()
    assert hk_latest["as_of"] == date(2026, 1, 20).isoformat()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/worker/test_tasks.py::test_refresh_daily_watchlist_analysis_task_stores_reports_for_each_symbol -v`

Expected: FAIL because `refresh_daily_watchlist_analysis` is not defined.

- [ ] **Step 3: Implement watchlist task**

Add to `apps/worker/tasks/reports.py`:

```python
from packages.shared.config import settings


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
```

- [ ] **Step 4: Run worker tests**

Run: `python -m pytest tests/worker/test_tasks.py -v`

Expected: PASS.

### Task 4: Document watchlist operation

**Files:**
- Modify: `docker-compose.yml`
- Modify: `docs/runbooks/local-development.md`

- [ ] **Step 1: Add watchlist environment variable**

Add this variable to both `worker.environment` and `beat.environment` in `docker-compose.yml`:

```yaml
DAILY_REPORT_WATCHLIST: AAPL:US
```

- [ ] **Step 2: Update runbook**

Add this section to `docs/runbooks/local-development.md`:

```markdown
## 配置每日股票池

默认定时任务会读取：

```bash
DAILY_REPORT_WATCHLIST=AAPL:US
```

多个股票用英文逗号分隔，格式为 `SYMBOL:MARKET`：

```bash
DAILY_REPORT_WATCHLIST=AAPL:US,0700:HK,600519:CN
```
```

### Task 5: Verify watchlist scheduling

**Files:**
- Test: `tests/worker/test_celery_schedule.py`
- Test: `tests/worker/test_tasks.py`
- Test: `tests/api/test_reports_api.py`
- Test: `apps/web/app/page.test.tsx`

- [ ] **Step 1: Run targeted backend tests**

Run: `python -m pytest tests/worker/test_celery_schedule.py tests/worker/test_tasks.py tests/api/test_reports_api.py -v`

Expected: PASS.

- [ ] **Step 2: Run frontend tests**

Run: `npm run test:web`

Expected: PASS.

- [ ] **Step 3: Run Ruff**

Run: `python -m ruff check packages/shared/config.py apps/worker/celery_app.py apps/worker/tasks/reports.py tests/worker/test_celery_schedule.py tests/worker/test_tasks.py tests/api/test_reports_api.py`

Expected: `All checks passed!`.

- [ ] **Step 4: Validate compose services**

Run: `docker compose config --services`

Expected: output includes `db`, `redis`, `beat`, and `worker`.
