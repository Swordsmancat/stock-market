# Parallel Remaining Backlog Execution Design

## Overview

This task coordinates the next implementation wave after the previous Phase 1/2 work. The project now has Trellis tracked in git, market-data resilience improvements, ingestion quality diagnostics, and task-runs empty/error state handling. The next wave should reduce remaining process risk first, then add focused tests and design follow-ups.

## Workstream Model

### Lane A: Backend guideline bootstrap

Purpose: fill `.trellis/spec/backend/*` with actual project conventions and code examples.

Expected files:

- `.trellis/spec/backend/index.md`
- `.trellis/spec/backend/directory-structure.md`
- `.trellis/spec/backend/database-guidelines.md`
- `.trellis/spec/backend/error-handling.md`
- `.trellis/spec/backend/logging-guidelines.md`
- `.trellis/spec/backend/quality-guidelines.md`

Concurrency: can run in parallel with frontend guideline bootstrap and code-test lanes, but should not be edited by another Trellis-state agent at the same time.

### Lane B: Frontend guideline bootstrap

Purpose: fill `.trellis/spec/frontend/*` with actual Next.js/React project conventions and code examples.

Expected files:

- `.trellis/spec/frontend/index.md`
- `.trellis/spec/frontend/directory-structure.md`
- `.trellis/spec/frontend/component-guidelines.md`
- `.trellis/spec/frontend/hook-guidelines.md`
- `.trellis/spec/frontend/state-management.md`
- `.trellis/spec/frontend/type-safety.md`
- `.trellis/spec/frontend/quality-guidelines.md`

Concurrency: can run in parallel with backend guideline bootstrap and backend-only planning lanes.

### Lane C: Deferred API proxy and client interaction tests

Purpose: complete the previously deferred Lane E by adding focused frontend tests without changing backend contracts.

Expected files:

- `apps/web/app/api/**/route.ts` tests if the current test setup supports route handlers.
- `apps/web/components/**.test.tsx` for one high-value client interaction.
- Existing related page/component tests if colocated patterns require updates.

Concurrency: should not run concurrently with broad frontend page rewrites. It can run with spec bootstrap lanes.

### Lane D: Ingestion single-fetch design

Purpose: produce a small design or implementation plan for avoiding duplicate real-provider fetches during ingestion.

Expected files:

- Prefer design-only Trellis artifact or plan note in child task.
- Implementation, if later approved, would touch `packages/services/ingestion.py` and ingestion tests.

Concurrency: design-only lane can run in parallel. Implementation should wait to avoid overlapping with data-quality ingestion code.

### Lane E: TaskRun quality diagnostics design

Purpose: define how `quality_diagnostics` should be written into TaskRun result and shown in the TaskRun detail UI.

Expected files:

- Prefer design-only child task initially.
- Later implementation may touch `packages/services/task_runs.py`, worker tasks, `apps/web/app/[locale]/task-runs/[taskRunId]/page.tsx`, and tests.

Concurrency: design-only lane can run in parallel. Implementation should be a separate cross-layer task.

## Sequential Boundaries

1. Main agent owns Trellis task creation, parent/child links, final status updates, commits, and pushes.
2. Guideline bootstrap lanes may edit different spec folders in parallel, but final review should check consistency.
3. Frontend test lane should not overlap with any UI feature implementation lane.
4. Backend ingestion and TaskRun implementation should wait until their design lanes are reviewed.

## Git Policy

- Subagents must not commit or push.
- Main agent commits only after reviewing combined diffs and after user approval.
- Push requires explicit user approval.
