# Live Full-Market Pipeline Acceptance and Production Hardening Plan

## Planning and Task Split

- [ ] Review and approve the parent PRD/design/plan.
- [ ] Create three child tasks from the design task map; keep this parent as the integration owner.
- [ ] Activate only `a-share-resumable-evidence-backfill` first.

## Child 1: Resumable Backend Pipeline

### Persistence and TaskRun reliability

- [ ] Add `ResearchEvidenceBackfill` ORM model and additive Alembic revision.
- [ ] Add nullable `TaskRun.heartbeat_at`; initialize/update it and use it for stale expiration with backward-compatible fallback.
- [ ] Add service serializers and state-transition helpers for queued/running/partial/succeeded/failed/cancel states.
- [ ] Add migration tests for PostgreSQL-compatible types and SQLite execution.
- [ ] Regression-test that active progress prevents stale expiration while genuinely stale legacy rows still expire.

### Provider and orchestration service

- [ ] Make AkShare bars distinguish valid empty data from import/network/schema failures without exposing raw payloads.
- [ ] Add deterministic universe freeze, stratified canary selection, five-way fundamental shards, and retry-set normalization helpers.
- [ ] Implement phase-specific daily-bar, fundamental, and local-indicator batches with batch size `1..100`, default 25.
- [ ] Persist checkpoint/counters/retry sets/heartbeat after every bounded batch.
- [ ] Implement cooperative cancellation, resume lineage, retry-failed lineage, and idempotent replay.
- [ ] Implement sequential provider pacing and bounded transient retry; do not retry valid no-data in-place.
- [ ] Ensure one symbol failure cannot erase prior successful symbols or advance an unclassified cursor.
- [ ] Add service tests for all state transitions, crash/replay boundaries, multi-exchange ordering, partial success, provider errors, no-data, insufficient indicators, and no silent fallback.

### Coverage, API, worker, and schedule

- [ ] Implement the shared current-evidence coverage projection and threshold evaluation.
- [ ] Add FastAPI create/get/resume/retry-failed/cancel routes and evidence-coverage route.
- [ ] Add TaskRun dispatcher and Celery worker for `ingestion.backfill_a_share_research_evidence`.
- [ ] Add overlap protection for API and Beat-triggered runs.
- [ ] Configure `Asia/Shanghai` explicitly and add 18:30 weekday bars/indicators plus rotating fundamental-shard schedules.
- [ ] Update synchronous Celery test support.
- [ ] Add API, dispatch, worker, schedule, coverage-query-count, and threshold tests.

### Child 1 validation

- [ ] Run focused provider/service/API/worker/migration tests.
- [ ] Run Ruff on touched Python files and `git diff --check`.
- [ ] Run Trellis check before committing child 1.
- [ ] Update the A-share research and data-job specs with the final executable contracts.

## Child 2: AI Research Operations UI

- [ ] Add no-store Next.js proxies for coverage, create, resume, retry-failed, cancel, and run detail.
- [ ] Add `AshareEvidenceCoveragePanel` and compose it into AI Research without duplicating discovery state.
- [ ] Render overall and exchange coverage, thresholds, provider/freshness, progress, failures, retry preview, and TaskRun links.
- [ ] Add guarded start-canary/start-baseline/resume/retry-failed/cancel interactions.
- [ ] Keep empty/error/partial/stale/provider-failed states distinct and localized.
- [ ] Update English and Chinese message catalogs together.
- [ ] Add route-proxy, component-interaction, and server-page tests.
- [ ] Run focused Vitest, full `npm run test:web`, TypeScript `--noEmit`, locale JSON parse, and `git diff --check`.
- [ ] Run desktop/mobile browser smoke after the backend contract is available.
- [ ] Run Trellis check and update frontend/backend specs if the implemented payload differs from design.

## Child 3: Isolated Live Acceptance

### Runtime harness

- [ ] Add an acceptance Compose override/project with `stock_acceptance`, isolated Redis, dedicated ports, and `APP_ENV=acceptance`.
- [ ] Add explicit setup, migration, startup, stop, cleanup, and retention commands.
- [ ] Add a mutating acceptance runner guarded by real-network and acceptance-write flags plus a database-name check.
- [ ] Unit-test argument guards, secret redaction, polling, failure classification, and artifact formatting without live network.

### Real execution sequence

- [ ] Record clean git commit, dependency/provider versions, migration head, timezone, and sanitized environment metadata.
- [ ] Run the existing non-mutating AkShare provider preflight.
- [ ] Start isolated API, Redis, worker, beat, and Web; verify health and Celery registration.
- [ ] Sync the real CN universe through API/TaskRun and record SSE/SZSE/BSE distribution and reconciliation history.
- [ ] Prove an empty/incomplete follow-up preserves the last good universe and manual rows using a deterministic safe test path.
- [ ] Run the deterministic 50-100 symbol canary through bars, fundamentals, indicators, discovery profiles, resume, and retry.
- [ ] Run at least two real corporate-action cursor batches and replay one batch to prove idempotency/citation stability.
- [ ] Run the full 18-month baseline, allowing stop/resume, and record final threshold evaluation.
- [ ] Run each discovery profile twice over unchanged evidence; record scope, timing, coverage, diagnostics, and ranking stability.
- [ ] Validate deterministic LLM fallback and citation/symbol rejection; use a live LLM only if already configured.
- [ ] Browser-check AI Research, Evidence Center, and TaskRun pages at desktop/mobile widths with console/network observations.

### Hardening loop

- [ ] Classify each live finding as product defect, provider limitation, environment/config issue, or accepted data gap.
- [ ] For product defects, add a failing regression first or reproduce with a focused fixture, then implement the smallest in-scope fix.
- [ ] Repeat focused checks after each fix and repeat only the affected live acceptance slice.
- [ ] Do not lower thresholds or reclassify provider failures as no-data merely to make acceptance pass.

### Documentation and final gates

- [ ] Write a sanitized acceptance report under the task evidence directory.
- [ ] Update the A-share runbook with setup, preflight, baseline, incremental, resume, retry, cancel, schedules, abort conditions, and cleanup.
- [ ] Update README/user guide status only to the level supported by real evidence.
- [ ] Run full backend tests, full Web tests, TypeScript, touched Ruff, migration checks, locale parse, Trellis validation, and `git diff --check`.
- [ ] Verify no secrets or raw upstream payloads appear in git diff or acceptance artifacts.
- [ ] Commit each child logically, archive children, then run parent cross-child review and archive this parent.

## Risk and Rollback Points

- [ ] Before migration: verify the target database is `stock_acceptance` for live acceptance.
- [ ] Before provider writes: require read-only preflight success and explicit write opt-in.
- [ ] After each bounded batch: verify checkpoint and evidence commits before moving the cursor.
- [ ] On provider-wide schema/rate failure: stop the run, preserve checkpoint, and do not flood retries.
- [ ] On coverage below threshold: retain partial state/retry set and report failure; do not delete successful evidence.
- [ ] On schedule overlap: reuse/skip the active run and record the decision.
- [ ] Rollback code by disabling schedules and reverting additive routes/tasks; preserve evidence unless the user separately authorizes deletion.
