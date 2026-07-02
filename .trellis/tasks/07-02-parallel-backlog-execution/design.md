# Parallel Backlog Execution Design

## Overview

This task coordinates the next implementation round after the current backlog audit. The project already has stable MVP foundations and recently added diagnostics. The next work should be split into subagent lanes only when file ownership and validation can be kept independent.

## Workstream Model

### Lane A: Trellis and plan state synchronization

Purpose: reconcile task state and historical plan documents with already completed work.

Expected areas:

- `.trellis/tasks/**`
- `docs/superpowers/plans/**`

Concurrency: sequential only. These files represent workflow state and should not be edited by multiple agents at the same time.

### Lane B: Backend indicator and provider resilience

Purpose: improve API behavior for empty data, insufficient data, provider failures, and effective provider reporting.

Expected areas:

- `packages/services/market_data.py`
- `apps/api/routers/market_data.py` if API error mapping is needed
- `tests/services/test_market_data_service.py`
- `tests/api/test_market_data_api.py`
- `tests/api/test_market_data_db_api.py`

Concurrency: can run in parallel with frontend-only or docs-only lanes, but not with another backend market-data agent.

### Lane C: Data quality integration

Purpose: wire the pure data quality service into ingestion or TaskRun results without changing provider code.

Expected areas:

- `packages/services/ingestion.py`
- `packages/services/data_quality.py` only if small extension is needed
- `packages/services/task_runs.py` if result shaping is needed
- `tests/services/test_ingestion_service.py`
- `tests/services/test_data_quality.py`

Concurrency: can run in parallel with frontend-only work, but should not run concurrently with broad TaskRun/Celery changes.

### Lane D: Frontend error states and i18n cleanup

Purpose: reduce silent fallbacks, improve locale-aware display, and remove high-value hardcoded strings.

Expected areas:

- `apps/web/app/[locale]/**`
- `apps/web/components/**`
- `apps/web/messages/*.json`
- related Vitest page/component tests

Concurrency: can run in parallel with backend lanes if no API contract changes are required. If backend response shape changes, this lane should wait for backend design.

### Lane E: Tests and CI gates

Purpose: add focused tests for API route proxies, client forms, and optional lightweight CI gates.

Expected areas:

- `apps/web/app/api/**`
- `apps/web/components/**.test.tsx`
- `.github/workflows/ci.yml`
- `.github/workflows/dev-health.yml`

Concurrency: can run in parallel only when test targets do not overlap with frontend implementation files being edited.

## Sequential Gates

1. Synchronize Trellis and plan state first, so agents do not re-open completed work.
2. Run backend and frontend implementation lanes only after file ownership is explicit.
3. Run review agents after each implementation lane.
4. Run final verification once all lanes are merged into the main worktree.

## Git Policy

- Implementation subagents must not commit or push.
- The main agent stages and commits only after reviewing combined diffs.
- Push requires explicit user approval.
