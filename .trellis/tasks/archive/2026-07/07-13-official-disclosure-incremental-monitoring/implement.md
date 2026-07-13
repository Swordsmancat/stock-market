# Implementation plan

## Steps

1. Add the monitoring-state ORM model and Alembic migration.
2. Extend configuration with bounded interval, overlap, freshness, retry, and document-limit defaults.
3. Add incremental cursor/retry/freshness behavior to official disclosure operations while preserving explicit batch compatibility and extracted-document dedupe.
4. Thread `mode` and TaskRun identity through dispatch and worker execution; add the Beat scheduler task and schedule.
5. Add the operator API route and Next.js proxy.
6. Extend Evidence Center types, controls, monitoring metrics, per-symbol states, and English/Chinese localization.
7. Add focused service, API, worker schedule/task, dispatcher, proxy, component, and migration compatibility tests.
8. Update the operational contract, README, parent task, and task acceptance record.
9. Run focused checks, full backend/frontend regression, Trellis Check, migration validation, and finish-work; commit and push each completed task state.

## Validation

- `python -m pytest tests/services/test_official_disclosure_operations.py tests/api/test_official_disclosures_api.py tests/services/test_task_dispatch.py tests/worker/test_tasks.py tests/worker/test_celery_schedule.py tests/shared/test_alembic_compat.py`
- `npm --prefix apps/web test -- --run components/official-disclosure-evidence-panel.test.tsx app/api/official-disclosures/watchlist-monitor/route.test.ts app/api/official-disclosures/watchlist-ingest/route.test.ts`
- `python -m pytest`
- `npm --prefix apps/web test -- --run`
- repository lint/type-check commands discovered from project configuration

## Risk and rollback points

- Cursor correctness: retain overlap and identity dedupe; never use a strictly exclusive timestamp boundary.
- Task concurrency: keep one task name/mutex for scheduled and explicit flows.
- Provider load: preserve sequential calls, delay floor, lookback/document caps, and per-symbol backoff.
- Failure recovery: commit successful state transitions independently and never clear the last successful cursor on failure.
- UI compatibility: additive response fields only; preserve the current evidence table and exact-PDF ingestion action.

## Start gate

- The user explicitly approved continuing with the recommended implementation and automatic execution.
- Planning artifacts contain no unresolved product-intent questions.
