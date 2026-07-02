# Parallel Remaining Backlog Execution Plan

## Phase 1: Parent Planning

- [x] Create parent task for parallel remaining backlog execution.
- [x] Write parent PRD.
- [x] Write parent design with parallel-safe lanes.
- [x] Write implementation plan and validation policy.
- [x] Create child tasks for approved lanes.
- [x] Ask user for implementation-launch approval.

## Phase 2: Parallel Lane Candidates

### Lane A: Backend guideline bootstrap

- [x] Fill backend Trellis guidelines from actual code patterns.
- [x] Include real file path examples.
- [x] Update backend index statuses.
- [x] Review for consistency with current FastAPI/SQLAlchemy/Celery patterns.

Validation:

```bash
python ./.trellis/scripts/task.py validate 00-bootstrap-guidelines
```

### Lane B: Frontend guideline bootstrap

- [x] Fill frontend Trellis guidelines from actual Next.js/React patterns.
- [x] Include real file path examples.
- [x] Update frontend index statuses.
- [x] Review for consistency with next-intl, server actions, and Vitest patterns.

Validation:

```bash
python ./.trellis/scripts/task.py validate 00-bootstrap-guidelines
```

### Lane C: Deferred API proxy and client interaction tests

- [x] Pick one or two high-value API proxy routes.
- [x] Add focused route/client interaction tests.
- [x] Avoid backend contract changes.

Validation:

```bash
npm run test:web
```

### Lane D: Ingestion single-fetch design

- [x] Map current ingestion data flow and double-fetch source.
- [x] Propose minimal refactor plan.
- [x] Identify tests needed before implementation.

Validation:

```bash
python -m pytest tests/services/test_ingestion_service.py tests/services/test_data_quality.py -v
```

### Lane E: TaskRun quality diagnostics design

- [x] Define TaskRun result contract for quality diagnostics.
- [x] Define frontend TaskRun detail display shape.
- [x] Identify backend/frontend tests needed before implementation.

Validation:

```bash
python -m pytest tests/services/test_task_runs_service.py tests/services/test_task_dispatch.py -v
npm run test:web
```

## Phase 3: Reviews

- [x] Run focused spec review for each completed implementation lane.
- [x] Run focused quality review for each completed implementation lane.
- [x] Resolve blocking review findings.

## Phase 4: Final Verification

- [x] Run validation commands for changed areas.
- [x] Run `git diff --stat` and `git status --short --branch`.
- [x] Summarize completed lanes and remaining deferred items.

Summary:

- Lane A completed backend Trellis guidelines with real FastAPI, SQLAlchemy, Celery, diagnostics, and pytest examples. Backend spec review is approved.
- Lane B completed frontend Trellis guidelines with real Next.js App Router, next-intl, Server Actions, API proxy, component, state, type-safety, and Vitest examples. Frontend spec review is approved.
- Lane C added focused API proxy route tests for task-run retry forwarding and upstream failure propagation.
- Lane D produced the ingestion single-fetch design. Production implementation remains deferred.
- Lane E produced the TaskRun quality diagnostics persistence/display design. Production implementation remains deferred.
- Final validation passed: `python ./.trellis/scripts/task.py validate 00-bootstrap-guidelines`, `npm run test:web`, and placeholder/wrong-path scan for Trellis specs.

Remaining deferred implementation items:

- Implement ingestion single-fetch refactor from the Lane D design.
- Persist ingestion `quality_diagnostics` in TaskRun result payloads from the worker.
- Add a dedicated quality diagnostics section to the TaskRun detail UI.
- Continue adding focused API proxy/client interaction coverage as more high-value routes are identified.

## Phase 5: Commit and Push Policy

- [x] Ask user before committing.
- [x] Commit reviewed scope only.
- [x] Push only after explicit user approval.

Committed and pushed as `7e8e4b9 feat: bootstrap Trellis specs and proxy tests`.
