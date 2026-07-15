# Quality Guidelines

> Current backend quality, testing, and safety conventions.

---

## Overview

Backend quality is protected mostly by focused pytest coverage, SQLite-backed persistence tests, script-level diagnostic tests, and worker task tests. The current repository favors small layer-specific tests over broad end-to-end suites, and it uses non-mutating diagnostics for local readiness checks.

Concrete examples:

- `tests/api/test_ingestion_api.py`, `tests/api/test_market_data_api.py`, and `tests/api/test_task_runs_api.py` exercise FastAPI router behavior.
- `tests/services/test_market_data_service.py`, `tests/services/test_report_service.py`, and `tests/services/test_watchlists_service.py` cover service-layer business behavior.
- `tests/scripts/test_provider_readiness.py`, `tests/scripts/test_dev_health_check.py`, and `tests/scripts/test_task_run_health.py` lock diagnostic script semantics.
- `tests/worker/test_tasks.py` and `tests/worker/test_celery_schedule.py` cover Celery task behavior and schedule configuration.
- `tests/helpers/celery_sync.py` provides synchronous Celery execution for API tests that need task-run behavior without a live worker.

---

## Required Patterns

### Keep layer boundaries testable

New backend behavior should fit the existing layer boundaries so focused tests can cover it:

- Routers should call services, as in `apps/api/routers/ingestion.py`, `apps/api/routers/fundamentals.py`, and `apps/api/routers/task_runs.py`.
- Services should accept explicit sessions where they touch the database, as in `packages/services/ingestion.py`, `packages/services/watchlists.py`, and `packages/services/task_runs.py`.
- Providers should stay behind `ProviderAdapter`, as in `packages/providers/base.py`, `packages/providers/mock_provider.py`, and `packages/providers/yfinance_provider.py`.
- Workers should call services and record `TaskRun` lifecycle state, as in `apps/worker/tasks/ingestion.py`, `apps/worker/tasks/reports.py`, and `apps/worker/tasks/alerts.py`.
- The only current no-TaskRun worker exception is the direct periodic
  `alerts.evaluate_watchlist_alerts` delivery when a local persisted preflight
  proves there are no actionable alert rules and no `task_run_id` was supplied.
  The exact boundary and required regressions live in
  `error-handling.md#scenario-direct-periodic-alert-no-op-suppression`.

### Preserve non-mutating diagnostics

Diagnostics that are documented as read-only should remain read-only:

- `scripts/provider_readiness.py` states that it smoke-checks providers without database writes; `tests/scripts/test_provider_readiness.py` verifies provider status output.
- `scripts/task_run_health.py` describes read-only `TaskRun` reliability checks; `tests/scripts/test_task_run_health.py` verifies stale running tasks are not mutated.
- `scripts/dev_health_check.py` checks local services and prints suggested fixes; tests in `tests/scripts/test_dev_health_check.py` assert output and exit-code behavior.

Scripts that do perform runtime actions should make that clear in their name and output. For example, `scripts/mvp_acceptance.py` probes a running API and prints `PASS` / `FAIL` checks, while `scripts/verify_celery.py` checks imports, Redis connectivity, and task registration.

---

## Testing Requirements

Use the smallest focused pytest target that covers the changed backend layer.

Observed test patterns:

- API tests use `TestClient(app)` and override `get_session()` when database state matters. Example: `tests/api/test_ingestion_api.py`.
- Service tests create in-memory SQLite sessions with `create_engine(..., poolclass=StaticPool)` and `Base.metadata.create_all(engine)`. Examples: `tests/services/test_report_service.py`, `tests/services/test_watchlists_service.py`, and `tests/services/test_news_service.py`.
- Script tests call `main()` or pure helper functions and assert status text, exit codes, and suggestions. Examples: `tests/scripts/test_provider_readiness.py`, `tests/scripts/test_dev_health_check.py`, and `tests/scripts/test_task_run_health.py`.
- Worker tests monkeypatch `SessionLocal` to a test session and assert `TaskRun` state. Examples: `tests/worker/test_tasks.py` and `tests/helpers/celery_sync.py`.
- Celery schedule tests inspect `celery_app.conf.beat_schedule` directly. Example: `tests/worker/test_celery_schedule.py`.

Useful focused commands include:

```bash
pytest tests/api/test_ingestion_api.py
pytest tests/services/test_market_data_service.py
pytest tests/scripts/test_provider_readiness.py tests/scripts/test_task_run_health.py
pytest tests/worker/test_tasks.py tests/worker/test_celery_schedule.py
```

For Trellis guideline validation, use:

```bash
python ./.trellis/scripts/task.py validate 00-bootstrap-guidelines
```

If validation fails because another layer such as frontend guidelines is still unfilled, record that reason and do not modify out-of-scope frontend files.

---

## Safety Boundaries for Subagents

Backend subagents should keep changes scoped to the files they were assigned.

For this guideline work specifically:

- Do not edit `apps/api/**`, `apps/worker/**`, `packages/**`, `scripts/**`, or `tests/**` unless the user explicitly expands scope.
- Do not edit `.trellis/spec/frontend/**` from a backend lane.
- Do not update `.trellis/tasks/**` task status, checklist, or task metadata from a lane that was only asked to fill backend guidelines.
- Do not create git commits or push branches unless the user explicitly asks. This matches the project workflow and the lane instruction for backend spec bootstrap work.

These safety boundaries complement the source patterns in `apps/api/main.py`, `packages/services/market_data.py`, `packages/providers/base.py`, `packages/domain/models.py`, and `apps/worker/celery_app.py`; they keep documentation work from accidentally changing runtime behavior.

---

## Forbidden Patterns

- Do not replace focused tests with broad live-service checks when a SQLite or monkeypatched test already covers the layer.
- Do not add tests that require real provider network access by default. `scripts/provider_readiness.py` requires explicit `--real-network` for yfinance, and `tests/scripts/test_provider_readiness.py` uses fakes.
- Do not mutate database rows in health checks that are documented as read-only. `tests/scripts/test_task_run_health.py` asserts stale running task rows remain `running`.
- Do not bypass `tests/helpers/celery_sync.py` by requiring a live Celery worker in API tests.
- Do not commit or push from a subagent lane unless the user explicitly asks for git history changes.

---

## Review Checklist

When reviewing backend work, check that:

- Router changes remain thin and delegate to services, following `apps/api/routers/market_data.py`, `apps/api/routers/ingestion.py`, and `apps/api/routers/task_runs.py`.
- Database work follows `packages/shared/database.py`, `packages/domain/models.py`, and Alembic patterns under `alembic/versions/`.
- Provider changes preserve the `ProviderAdapter` boundary from `packages/providers/base.py` and service wrapping in `packages/services/market_data.py`.
- Worker changes preserve `TaskRun` lifecycle behavior from `apps/worker/tasks/ingestion.py`, `apps/worker/tasks/reports.py`, and `packages/services/task_runs.py`.
- Direct periodic alert suppression is limited to the documented no-rule
  preflight; supplied TaskRuns, actionable evaluations, and all repeated errors
  remain persisted and test-covered.
- Diagnostics keep their documented `OK` / `WARN` / `FAIL` or `PASS` / `FAIL` semantics and avoid accidental writes.
- Tests are focused on the changed layer and do not require real PostgreSQL, Redis, Celery, or provider network access unless the command explicitly says so.
