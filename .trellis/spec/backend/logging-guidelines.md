# Logging Guidelines

> Current logging and diagnostic-output conventions for the backend.

---

## Overview

Current backend logging is intentionally light. The repository has a small shared logging helper in `packages/shared/logging.py`, but application code has not standardized on a project-wide structured logging schema or consistent logger usage yet. Most observable output today comes from diagnostic scripts using `print()`, Alembic using its generated logging configuration, FastAPI returning HTTP error payloads, and Celery task state being persisted to `TaskRun` rows instead of emitted as logs.

Concrete examples:

- `alembic/env.py` calls `fileConfig(config.config_file_name)` when an Alembic config file is present.
- `packages/shared/logging.py` defines `configure_logging(...)` and `get_logger(...)` as lightweight helpers.
- `scripts/provider_readiness.py` renders `OK` / `WARN` / `FAIL` readiness lines to stdout.
- `scripts/dev_health_check.py` renders local service health summaries and suggested fixes to stdout.
- `scripts/task_run_health.py` renders read-only `TaskRun` reliability state without tracebacks.
- `scripts/verify_celery.py` prints `FAIL:` / `OK:` lines for Celery import, Redis, and task-registration checks.
- `packages/services/task_runs.py` and `apps/worker/tasks/reports.py` persist task status, result payloads, and error messages to database rows instead of logging through a logger.

---

## Current State

There is a lightweight shared helper in `packages/shared/logging.py`, but there is no enforced structured logging schema and no consistent `get_logger(__name__)` usage pattern across application code. Do not invent a logging framework while making small backend changes. If a feature needs observability today, follow the existing boundary for that runtime:

- API errors: return explicit `HTTPException` details where a router already owns mapping, as in `apps/api/routers/market_data.py` and `apps/api/routers/task_runs.py`.
- Worker execution: record state in `TaskRun` through `packages/services/task_runs.py`, as used by `apps/worker/tasks/ingestion.py`, `apps/worker/tasks/reports.py`, and `apps/worker/tasks/alerts.py`.
- Narrow exception: a direct periodic alert delivery with no supplied TaskRun
  may return the existing bounded `skipped/no_alert_rules` Celery result without
  database persistence after a local actionable-rule preflight. This is a
  no-work optimization, not log-only reporting; see the executable scenario in
  `error-handling.md`.
- Diagnostics: print concise status lines and suggestions, as in `scripts/provider_readiness.py`, `scripts/dev_health_check.py`, and `scripts/task_run_health.py`.
- Migrations: keep Alembic's config-driven logging in `alembic/env.py`.

---

## Diagnostic Output Levels

Diagnostic scripts currently use status labels rather than Python log levels.

Observed conventions:

- `OK` means the checked dependency or invariant is healthy. Examples: `scripts/provider_readiness.py`, `scripts/dev_health_check.py`, `scripts/verify_celery.py`.
- `WARN` means local development can continue but a dependency, provider check, or task-run state needs attention. Examples: `scripts/provider_readiness.py` for yfinance without `--real-network`, `scripts/dev_health_check.py` for API/Redis/Celery availability, and `scripts/task_run_health.py` for stale or failed task runs.
- `FAIL` means the script's primary check failed and, for scripts with failure exit codes, should return nonzero. Examples: `scripts/provider_readiness.py` for unknown providers, `scripts/dev_health_check.py` for frontend failures, and `scripts/verify_celery.py` for Redis or registration failures.
- `PASS` / `FAIL` is used by acceptance probing in `scripts/mvp_acceptance.py`.

Tests that lock this behavior include `tests/scripts/test_provider_readiness.py`, `tests/scripts/test_dev_health_check.py`, and `tests/scripts/test_task_run_health.py`.

---

## What to Record

Use the existing output channel for the runtime instead of adding unrelated prints.

Current examples:

- Store task lifecycle details in `TaskRun`: `task_name`, `status`, `started_at`, `finished_at`, `duration_ms`, `input_json`, `result_json`, `error_message`, and `celery_task_id` in `packages/domain/models.py` and `packages/services/task_runs.py`.
- Return provider failure context at the API boundary without exposing credentials: `apps/api/routers/market_data.py` includes `message`, `provider`, and `operation` for `MarketDataProviderError`.
- Print diagnostic detail and suggested fixes from scripts: `scripts/provider_readiness.py` prints provider, market, symbol, timeframe, and suggestions; `scripts/dev_health_check.py` prints service names and suggested commands; `scripts/task_run_health.py` prints stale and failed task names.
- Keep test assertions focused on observable status text rather than hidden logs. Examples: `tests/scripts/test_provider_readiness.py`, `tests/scripts/test_dev_health_check.py`, and `tests/scripts/test_task_run_health.py`.

---

## What Not to Record

Do not print or persist secrets. The current settings include secret-bearing values and connection strings in `packages/shared/config.py`, such as `llm_api_key`, `database_url`, `redis_url`, and provider tokens read by service code.

Sensitive-data boundaries:

- Do not log full API keys, LLM keys, Tushare tokens, `.env` contents, or authorization headers.
- Be careful with full database and Redis URLs. Existing scripts sometimes mention local Redis URLs, such as `scripts/verify_celery.py` and `scripts/dev_health_check.py`; do not expand this into printing credentials for non-local URLs.
- Do not include raw provider response payloads if they can contain account, quota, token, or request metadata. Provider code examples include `packages/providers/yfinance_provider.py`, `packages/providers/tushare_provider.py`, and `packages/providers/akshare_provider.py`.
- Do not store sensitive input values in `TaskRun.input_json` or `TaskRun.error_message`. Existing task inputs are market, symbol, date range, provider, watchlist, and retry metadata in `packages/services/task_runs.py` and `packages/services/task_dispatch.py`.

---

## Common Mistakes

- Do not add noisy `print()` calls to routers or services. Current print-style output belongs to standalone scripts.
- Do not add a new structured logging dependency unless the user asks for a logging feature or a broader observability change.
- Do not replace `TaskRun` persistence with log-only worker reporting. The only
  current exception is the documented direct periodic alert no-rule preflight;
  explicit TaskRuns, actual evaluations, and failures are never exempt.
- Do not reveal secrets while trying to make diagnostic failures more helpful.
- Do not change `WARN` diagnostics to `FAIL` just to make logs look stricter; current tests and local-development semantics distinguish warnings from failures.
