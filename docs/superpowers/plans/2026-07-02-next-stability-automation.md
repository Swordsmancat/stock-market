# Next Stability Automation Implementation Plan

> **Status: completed.** This plan was executed through subagent lanes and committed in `ed0276f feat: add stability automation diagnostics`. The unchecked boxes below are preserved as the original execution checklist, not as the current backlog. Implemented artifacts include `.github/workflows/dev-health.yml`, `scripts/provider_readiness.py`, `packages/services/data_quality.py`, `scripts/task_run_health.py`, their focused tests, and the local development runbook updates. Final verification reported focused backend tests, health checks, adjacent regression tests, and `npm run test:web` passing.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the next stabilization backlog into automated, verifiable workstreams that keep the stock analysis platform bootable, observable, and safe to extend.

**Architecture:** Keep the existing FastAPI + Celery + Next.js architecture. Add small diagnostic scripts and targeted CI automation rather than broad rewrites; each workstream should be independently testable and non-destructive by default.

**Tech Stack:** GitHub Actions, Python 3.13, pytest, FastAPI/Uvicorn, Redis, PostgreSQL/TimescaleDB, Celery, Next.js/Vitest, existing provider/service modules.

---

## Priority Order

1. **CI health automation**: scheduled/manual workflow that proves the health check can run from a clean checkout.
2. **Provider readiness smoke**: CLI for mock/yfinance provider readiness with real-network checks opt-in.
3. **Data quality checks**: reusable service that finds market data gaps and invalid OHLCV rows.
4. **TaskRun/Celery reliability diagnostics**: CLI/service checks for stale running tasks and broker readiness.
5. **Final verification**: run focused tests, health checks, and diff review before any commit.

## Task 1: Scheduled Dev Health Workflow

**Files:**
- Create: `.github/workflows/dev-health.yml`
- Modify: `docs/runbooks/local-development.md`

- [ ] **Step 1: Add a workflow that runs manually and daily**

Create `.github/workflows/dev-health.yml` with a `workflow_dispatch` trigger and a daily schedule. The workflow should:

- Run on `ubuntu-latest`.
- Start PostgreSQL/TimescaleDB and Redis services.
- Install Python 3.13 and Node 22.
- Run `python -m pip install -e ".[dev]"`.
- Run `npm ci`.
- Run `alembic upgrade head`.
- Start API in the background with `uvicorn apps.api.main:app --host 127.0.0.1 --port 8000`.
- Start web in the background with `npm run dev:web`.
- Poll `/health` and `/zh` before running checks.
- Run `python scripts/dev_health_check.py`.
- Run `python -m pytest tests/scripts/test_dev_health_check.py tests/api/test_health.py tests/services/test_task_dispatch.py -v`.
- Upload API/web logs when the workflow fails.

- [ ] **Step 2: Document the workflow**

In `docs/runbooks/local-development.md`, add a short subsection named `CI 健康检查自动化` explaining that the workflow is manual + scheduled and that it does not mutate code or production data.

- [ ] **Step 3: Verify workflow YAML and related checks**

Run:

```bash
python -m pytest tests/scripts/test_dev_health_check.py tests/api/test_health.py tests/services/test_task_dispatch.py -v
```

Expected: all selected tests pass.

## Task 2: Provider Readiness Smoke CLI

**Files:**
- Create: `scripts/provider_readiness.py`
- Create: `tests/scripts/test_provider_readiness.py`
- Modify: `docs/runbooks/local-development.md`

- [ ] **Step 1: Implement a non-mutating provider readiness CLI**

Create `scripts/provider_readiness.py` with a default mock check and an explicit real provider option:

```bash
python scripts/provider_readiness.py --provider mock --market US
python scripts/provider_readiness.py --provider yfinance --market US --symbol AAPL --real-network
```

Rules:

- Default provider is `mock`.
- Real network checks require `--real-network`.
- The command prints `OK`, `WARN`, or `FAIL` and a summary line.
- The command does not write market data to the database.
- Exit code is `0` for `OK/WARN`, `1` for `FAIL`.

- [ ] **Step 2: Add tests for provider readiness output**

Test with monkeypatches so no real network access is needed:

- mock provider succeeds.
- unknown provider returns `FAIL`.
- yfinance without `--real-network` returns `WARN` explaining the opt-in requirement.
- yfinance with fake downloader returning bars returns `OK`.

- [ ] **Step 3: Document provider smoke usage**

Add a runbook subsection named `Provider readiness smoke` with mock and yfinance commands.

## Task 3: Market Data Quality Checks

**Files:**
- Create: `packages/services/data_quality.py`
- Create: `tests/services/test_data_quality.py`
- Modify: `docs/runbooks/local-development.md`

- [ ] **Step 1: Add a pure service for daily bar quality checks**

Create a service that accepts serialized daily bars and returns a result containing:

- missing dates for weekday sessions.
- invalid OHLC rows where `high < low`, `high < open`, `high < close`, `low > open`, or `low > close`.
- empty or negative volume warnings.
- count of checked bars.

The service should not query the database in its first iteration; callers pass bars explicitly.

- [ ] **Step 2: Add unit tests**

Cover:

- complete weekday series has no gaps.
- missing weekday is reported.
- invalid OHLC row is reported.
- zero volume is `WARN`, negative volume is `FAIL`.

- [ ] **Step 3: Document how this will feed future ingestion/report checks**

Add a runbook note explaining that the service is pure first, then can be wired into ingestion TaskRun results later.

## Task 4: TaskRun and Celery Reliability Diagnostics

**Files:**
- Create: `scripts/task_run_health.py`
- Create: `tests/scripts/test_task_run_health.py`
- Modify: `docs/runbooks/local-development.md`

- [ ] **Step 1: Add a non-mutating TaskRun health CLI**

Create `scripts/task_run_health.py` that:

- imports the app database settings.
- queries recent `TaskRun` records when a database is reachable.
- reports stale `running` tasks older than `TASK_RUN_STALE_MINUTES` as `WARN`.
- reports failed tasks in the last 24 hours as `WARN` with count and task names.
- does not call `expire_stale_task_runs()` and does not mutate status.

- [ ] **Step 2: Add tests with in-memory SQLite**

Cover:

- no task runs returns `OK`.
- stale running task returns `WARN`.
- recent failed task returns `WARN`.
- database connection failure returns `WARN`, not traceback.

- [ ] **Step 3: Document operational usage**

Add runbook commands for:

```bash
python scripts/task_run_health.py
python scripts/verify_celery.py
```

## Task 5: Final Verification and Handoff

**Files:**
- Verify: `.github/workflows/dev-health.yml`
- Verify: `scripts/provider_readiness.py`
- Verify: `packages/services/data_quality.py`
- Verify: `scripts/task_run_health.py`
- Verify: updated docs and tests.

- [ ] **Step 1: Run focused test suites**

Run:

```bash
python -m pytest tests/scripts/test_dev_health_check.py tests/scripts/test_provider_readiness.py tests/scripts/test_task_run_health.py tests/services/test_data_quality.py -v
```

Expected: all focused tests pass.

- [ ] **Step 2: Run existing health checks**

Run:

```bash
python scripts/dev_health_check.py
python scripts/verify_celery.py
```

Expected: commands exit `0` in a healthy local stack; if local infrastructure is intentionally stopped, output should clearly explain the dependency issue.

- [ ] **Step 3: Run adjacent regression**

Run:

```bash
python -m pytest tests/api/test_health.py tests/services/test_task_dispatch.py tests/providers/test_yfinance_provider.py -v
npm run test:web
```

Expected: all selected regression checks pass.

- [ ] **Step 4: Review diff**

Run:

```bash
git diff --stat
git status --short --branch
```

Expected: only files from this plan are changed. Do not commit or push unless the user explicitly asks.

## Subagent Execution Notes

- Run implementation tasks sequentially, not in parallel, because several tasks update the same runbook.
- Each task must return changed files, tests run, and whether it stayed in scope.
- Each implementation task should be followed by a spec review and a code quality review before moving to the next task.
- No subagent may commit or push unless the user explicitly requests it.

## Self-Review

- Spec coverage: The plan covers the recommended next list: CI health automation, provider readiness, data quality, TaskRun/Celery reliability, and final verification.
- Scope: Each task has a clear file boundary and can be tested independently.
- Safety: All scripts are diagnostic by default and do not mutate services, databases, or git state.
- Type consistency: Script names, test paths, and command names are used consistently across tasks.
