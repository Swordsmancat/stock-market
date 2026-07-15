# Error Handling

> Error-handling patterns currently used by the backend.

---

## Overview

The backend uses a small number of explicit error boundaries rather than a global exception framework. FastAPI routers map known service/provider failures to `HTTPException`, services return structured fallback payloads for expected missing data, worker tasks record `TaskRun` failures before re-raising, and diagnostic scripts report `OK` / `WARN` / `FAIL` style statuses.

Concrete examples:

- `apps/api/routers/market_data.py` maps `MarketDataProviderError` to HTTP 502 and `ValueError` to HTTP 400.
- `apps/api/routers/task_runs.py` maps missing or invalid task-run IDs to HTTP 404 by checking for `None` service results.
- `packages/services/market_data.py` wraps unexpected provider exceptions in `MarketDataProviderError` while allowing provider `ValueError` to propagate as client input errors.
- `apps/worker/tasks/ingestion.py`, `apps/worker/tasks/reports.py`, and `apps/worker/tasks/alerts.py` call `fail_task_run()` before re-raising task exceptions.
- `scripts/provider_readiness.py`, `scripts/dev_health_check.py`, and `scripts/task_run_health.py` return human-readable `WARN` / `FAIL` diagnostics instead of tracebacks for expected environmental failures.

---

## FastAPI Error Responses

Routers stay thin and only translate errors that are meaningful at the HTTP boundary.

Current patterns:

- `apps/api/routers/market_data.py` wraps service calls in `_call_market_data_service()`.
  - `MarketDataProviderError` becomes `HTTPException(status_code=502, detail={"message", "provider", "operation"})`.
  - `ValueError` becomes `HTTPException(status_code=400, detail=str(error))`.
- `apps/api/routers/task_runs.py` calls service functions that return `None` for missing or invalid IDs, then raises `HTTPException(status_code=404, detail="Task run not found")`.
- `apps/api/routers/fundamentals.py` currently does not map service fallback payloads to errors. Missing fundamentals can return an item of `None` from `packages/services/fundamentals.py`.
- `apps/api/routers/health.py` returns `{"status": "ok"}` directly and does not perform dependency checks.

Do not add broad `except Exception` blocks in routers unless the existing service boundary gives the router enough information to return a useful status code.

---

## Provider Boundary Errors

Provider adapters may raise provider-specific exceptions, but services are responsible for normalizing unexpected provider failures before they reach routers.

Observed provider/service boundary:

- `packages/providers/base.py` defines the `ProviderAdapter` protocol and `ProviderBar` / `ProviderInstrument` dataclasses used across providers.
- `packages/providers/yfinance_provider.py` raises `ValueError` for an unsupported timeframe, which remains a client/request error.
- `packages/services/market_data.py` defines `MarketDataProviderError(provider_name, operation, original_error)` for unexpected provider failures.
- `_fetch_provider_bars()` and `_fetch_provider_instruments()` in `packages/services/market_data.py` re-raise `ValueError` but wrap other exceptions as `MarketDataProviderError`.
- `apps/api/routers/market_data.py` translates that wrapped provider error to HTTP 502 with provider and operation details.

This means new provider adapters should expose ordinary Python errors, and service code should decide whether a failure is invalid input (`ValueError`) or provider failure (`MarketDataProviderError`).

---

## Service Fallback and Database Errors

Some service functions intentionally degrade to fallback payloads when database reads fail or no data exists.

Examples:

- `packages/services/market_data.py` catches `SQLAlchemyError` while reading database bars and falls back to provider data.
- `packages/services/fundamentals.py` catches `SQLAlchemyError`, calls `session.rollback()`, and then falls back to mock/provider fundamentals.
- `apps/worker/tasks/reports.py` catches `SQLAlchemyError` in `_default_watchlist_value()`, rolls back, and falls back to `settings.daily_report_watchlist`.
- `packages/services/task_runs.py` returns `None` for invalid UUID input in `get_task_run_payload()` and `retry_task_run_payload()` instead of raising.

Use fallback payloads only where the current user-facing behavior already treats missing database data as recoverable. Write paths such as `packages/services/ingestion.py`, `packages/services/watchlists.py`, and `packages/services/task_runs.py` currently commit or raise rather than silently swallowing write failures.

---

## Worker Task Errors

Celery tasks record task-run state before propagating failures.

Observed pattern:

- Open `session = SessionLocal()`.
- Resolve or create a `TaskRun` row.
- Run service logic in a `try` block.
- On success, call `finish_task_run(task_run, result_payload, session=session)` and return the payload.
- On exception, call `fail_task_run(task_run, str(exc), session=session)` and re-raise.
- Always close the session in `finally`.

Examples:

- `apps/worker/tasks/ingestion.py` records failures from `ingest_market_snapshot()`.
- `apps/worker/tasks/reports.py` records failures from `refresh_stock_analysis()` and watchlist report generation.
- `apps/worker/tasks/alerts.py` records failures from `evaluate_all_watchlist_alerts()`.
- `tests/worker/test_tasks.py` asserts a raised `RuntimeError("provider timeout")` is recorded as a failed `TaskRun`.

Do not convert worker task exceptions into successful return payloads unless the existing task-run lifecycle is also updated to represent that state.

---

## Diagnostic Script Status Semantics

Diagnostic scripts use explicit status labels and generally avoid tracebacks for expected environmental problems.

Current semantics:

- `scripts/provider_readiness.py` uses `ReadinessStatus.OK`, `ReadinessStatus.WARN`, and `ReadinessStatus.FAIL`.
  - Unknown provider, provider construction failure, fetch failure, or no bars produce `FAIL` and exit code `1`.
  - `yfinance` without `--real-network` produces `WARN` and exit code `0`.
- `scripts/dev_health_check.py` uses `HealthStatus.OK`, `HealthStatus.WARN`, and `HealthStatus.FAIL`.
  - Frontend page/port failures are `FAIL`.
  - API, Redis, and Celery dependency problems are commonly `WARN` so the script can still guide local setup.
  - `render_results()` returns nonzero only when a `FAIL` is present.
- `scripts/task_run_health.py` uses string constants `OK_STATUS` and `WARN_STATUS`.
  - Stale running tasks, recently failed tasks, or database unavailability produce `WARN`.
  - The script is read-only and returns exit code `0` even for warnings.
- `scripts/verify_celery.py` prints `FAIL:` and exits `1` for import, Redis, or task-registration failures; it prints `OK:` lines and exits `0` on success.
- `scripts/mvp_acceptance.py` prints `PASS` / `FAIL` per API check and exits `1` if any acceptance check fails.

Tests that lock these semantics include `tests/scripts/test_provider_readiness.py`, `tests/scripts/test_dev_health_check.py`, and `tests/scripts/test_task_run_health.py`.

---

## Common Mistakes

- Do not let raw provider exceptions cross directly into HTTP responses when `MarketDataProviderError` is the existing service boundary.
- Do not change diagnostic `WARN` conditions into failures without updating tests and the intended local-development semantics.
- Do not print tracebacks for expected diagnostic failures; current scripts render concise details and suggestions.
- Do not swallow worker exceptions after calling `fail_task_run()`; current worker tests expect the exception to propagate.
- Do not expose API keys, tokens, or connection secrets in error payloads. Current provider and diagnostic messages include provider names, task names, URLs, and exception summaries, but should not reveal secret values.

---

## Scenario: Empty Persisted Watchlist Daily Report

### 1. Scope / Trigger

- Trigger: `reports.refresh_daily_watchlist_analysis` runs without an explicit
  watchlist after the user has intentionally soft-removed every persisted item.
- Scope: default watchlist resolution and the watchlist-report worker TaskRun.
- Non-goals: Beat timing, provider retry, per-symbol partial failure, UI
  behavior, or automatic watchlist mutation.

### 2. Signatures

- Resolver: `_default_watchlist_value(session) -> str` in
  `apps/worker/tasks/reports.py`.
- Worker: `refresh_daily_watchlist_analysis(watchlist=None, start=None,
  end=None, ma_window=None, provider=None, task_run_id=None) -> dict[str,
  object]`.
- Persisted read: `get_active_watchlist_entries(session) -> list[tuple[str,
  str]]` in `packages/services/watchlists.py`.

### 3. Contracts

- A successful persisted read is authoritative, including `[]`. Historical
  inactive rows mean the user intentionally has no active scope; they prevent
  bootstrap reseeding and must resolve to the empty string.
- Only `SQLAlchemyError` from the persisted read rolls back and falls back to
  `settings.daily_report_watchlist`.
- An empty resolved list still creates or reuses the TaskRun, calls no market,
  provider, or AI analysis, and finishes succeeded with:

```json
{"status":"skipped","reason":"empty_watchlist","item_count":0,"items":[]}
```

- Explicit and persisted non-empty lists keep the existing report-generation
  and fail-plus-reraise semantics.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| No watchlist rows have ever existed | Existing watchlist service may seed configured defaults |
| Historical rows exist but all are inactive | Succeeded `skipped/empty_watchlist`; no analysis call |
| Persisted watchlist read raises `SQLAlchemyError` | Roll back and use configured fallback |
| Explicit empty string is supplied | Succeeded `skipped/empty_watchlist`; do not substitute persisted/configured items |
| One or more active entries exist | Refresh each entry using existing behavior |
| Non-empty entry analysis raises | Fail TaskRun and re-raise the original exception |

### 5. Good / Base / Bad Cases

- Good: the user removes the last item, the nightly task records a bounded
  skip, and the watchlist stays empty.
- Base: a fresh database has never held an item, so the existing bootstrap
  seeds `DAILY_REPORT_WATCHLIST` before the worker resolves its scope.
- Bad: use `entries or settings.daily_report_watchlist`; this treats an
  intentional empty list as a database failure and resurrects removed symbols.

### 6. Tests Required

- Worker regression uses SQLite, creates then soft-removes an item, patches
  `refresh_stock_analysis` to fail if called, and asserts the exact succeeded
  TaskRun result and empty input scope.
- Existing persisted non-empty, explicit non-empty, exception, and reused
  TaskRun tests must continue to pass.
- Watchlist service tests must keep asserting that soft removal returns zero
  active entries without reseeding historical rows.

### 7. Wrong vs Correct

#### Wrong

```python
entries = get_active_watchlist_entries(session)
return format_watchlist_entries(entries) if entries else settings.daily_report_watchlist
```

#### Correct

```python
try:
    entries = get_active_watchlist_entries(session)
except SQLAlchemyError:
    session.rollback()
    return settings.daily_report_watchlist
return format_watchlist_entries(entries)
```
