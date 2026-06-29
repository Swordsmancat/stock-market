# Task Run Observability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Record scheduled analysis task runs and expose the latest run status in the API and dashboard.

**Architecture:** Add a `task_runs` persistence model and service API for starting, completing, failing, and querying runs. Wrap `reports.refresh_daily_watchlist_analysis` so success and failure are recorded. Expose `/task-runs/recent` and `/task-runs/latest`, then show the latest daily report schedule status on the dashboard.

**Tech Stack:** Python, FastAPI, SQLAlchemy, Alembic, Celery, Next.js, pytest, Vitest, Ruff.

---

### Task 1: Persist task runs

**Files:**
- Modify: `packages/domain/models.py`
- Create: `alembic/versions/0004_task_runs.py`
- Modify: `tests/domain/test_migrations.py`
- Create: `packages/services/task_runs.py`
- Create: `tests/services/test_task_runs_service.py`

- [ ] **Step 1: Write service tests**

Create tests that start a run, finish it, fail another run, and query the latest run by task name.

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m pytest tests/services/test_task_runs_service.py -v`

Expected: FAIL because `packages.services.task_runs` does not exist.

- [ ] **Step 3: Implement model, migration, and service**

Add `TaskRun` with `task_name`, `status`, timestamps, duration, input/result JSON, and error message. Add service helpers `start_task_run`, `finish_task_run`, `fail_task_run`, `get_recent_task_runs_payload`, and `get_latest_task_run_payload`.

- [ ] **Step 4: Run service and migration tests**

Run: `python -m pytest tests/services/test_task_runs_service.py tests/domain/test_migrations.py -v`

Expected: PASS.

### Task 2: Record worker task runs

**Files:**
- Modify: `apps/worker/tasks/reports.py`
- Modify: `tests/worker/test_tasks.py`

- [ ] **Step 1: Write worker tests**

Assert `refresh_daily_watchlist_analysis` writes a succeeded run and records a failed run when the refresh raises.

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m pytest tests/worker/test_tasks.py -v`

Expected: FAIL until the worker writes task run records.

- [ ] **Step 3: Wrap the watchlist task**

Call `start_task_run` before refresh, `finish_task_run` on success, and `fail_task_run` on exception.

- [ ] **Step 4: Run worker tests**

Run: `python -m pytest tests/worker/test_tasks.py -v`

Expected: PASS.

### Task 3: Expose task run API

**Files:**
- Create: `apps/api/routers/task_runs.py`
- Modify: `apps/api/main.py`
- Create: `tests/api/test_task_runs_api.py`

- [ ] **Step 1: Write API tests**

Test `GET /task-runs/recent?limit=1` and `GET /task-runs/latest?task_name=reports.refresh_daily_watchlist_analysis`.

- [ ] **Step 2: Run tests to verify RED**

Run: `python -m pytest tests/api/test_task_runs_api.py -v`

Expected: FAIL because the router is not registered.

- [ ] **Step 3: Implement router and register it**

Add endpoints backed by `get_recent_task_runs_payload` and `get_latest_task_run_payload`.

- [ ] **Step 4: Run API tests**

Run: `python -m pytest tests/api/test_task_runs_api.py -v`

Expected: PASS.

### Task 4: Show latest run status on dashboard

**Files:**
- Modify: `apps/web/app/page.tsx`
- Modify: `apps/web/app/page.test.tsx`

- [ ] **Step 1: Update frontend test**

Mock `/task-runs/latest?task_name=reports.refresh_daily_watchlist_analysis` and assert the dashboard shows status and processed symbol count.

- [ ] **Step 2: Run frontend test to verify RED**

Run: `npm run test:web`

Expected: FAIL until the dashboard fetches and renders the latest run.

- [ ] **Step 3: Implement dashboard section**

Fetch the latest run payload and render `自动任务状态`.

- [ ] **Step 4: Run frontend test**

Run: `npm run test:web`

Expected: PASS.

### Task 5: Verify closure

**Files:**
- Tests across backend and frontend.

- [ ] **Step 1: Run targeted backend tests**

Run: `python -m pytest tests/services/test_task_runs_service.py tests/worker/test_tasks.py tests/api/test_task_runs_api.py tests/domain/test_migrations.py -v`

Expected: PASS.

- [ ] **Step 2: Run full tests and Ruff**

Run: `python -m pytest -v`, `npm run test:web`, and Ruff on changed Python files.

Expected: all PASS.
