# A-share Resumable Evidence Backfill Implementation

- [x] Read backend specs and search existing TaskRun/ingestion/coverage patterns.
- [x] Write failing model/migration and TaskRun heartbeat tests.
- [x] Add ORM model and Alembic revision.
- [x] Implement run lifecycle, deterministic scope/cohort/shards, checkpoint, cancellation, resume, retry sets, and overlap protection.
- [x] Write failing provider-outcome and phase-batch service tests.
- [x] Implement AkShare error distinction and phase-specific batch processing with idempotent persistence.
- [x] Write coverage projection and threshold tests, including constant/bounded query behavior.
- [x] Implement coverage service.
- [x] Write API, dispatch, worker, synchronous Celery, and schedule tests.
- [x] Implement routes, dispatcher, worker, progress/heartbeat, and Asia/Shanghai schedules.
- [x] Update backend contracts and runbook notes owned by this child.
- [x] Run focused tests and touched Ruff.
- [x] Run full backend tests, migration checks, Trellis validation, and `git diff --check`.
- [ ] Commit logically and archive this child before starting the UI child.

## Validation Results

- Full backend suite: `542 passed`.
- Touched-file Ruff: passed.
- Alembic head: `0015_research_evidence_backfills`.
- API route import/registration smoke: passed.
- Trellis task validation: passed.
- `git diff --check`: passed.
