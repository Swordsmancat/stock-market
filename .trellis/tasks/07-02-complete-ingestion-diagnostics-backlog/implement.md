# Complete Ingestion Diagnostics Backlog Implementation Plan

## Phase 1: Planning Artifacts

- [x] Create parent task.
- [x] Create child tasks for ingestion, TaskRun persistence, TaskRun UI, and proxy/client tests.
- [x] Write parent PRD.
- [x] Write parent technical design.
- [x] Write parent implementation plan.
- [x] Write child PRDs.
- [x] Curate implement/check context manifests.
- [ ] Ask user to approve implementation launch.

## Phase 2: Parallel Wave 1

### Lane A: Implement ingestion single-fetch

- [x] Add focused tests proving session-backed ingestion fetches instruments once and bars once per instrument.
- [x] Add or update serialized snapshot writer in `packages/services/ingestion.py`.
- [x] Ensure session and no-session paths compute `bar_count` from the same serialized snapshot.
- [x] Preserve diagnostics behavior and returned payload shape.
- [x] Validate with ingestion and data-quality tests.

Validation:

```bash
python -m pytest tests/services/test_ingestion_service.py tests/services/test_data_quality.py -v
```

### Lane D: Expand proxy/client interaction tests

- [x] Select one high-value route or client interaction that does not overlap TaskRun detail UI files.
- [x] Add focused frontend tests for request forwarding or user-visible interaction behavior.
- [x] Avoid backend contract changes and broad UI rewrites.
- [x] Validate with web tests.

Validation:

```bash
npm run test:web
```

## Phase 3: Sequential Backend Persistence

### Lane B: Persist TaskRun quality diagnostics

- [x] Update ingestion worker result payload to include `quality_diagnostics`.
- [x] Keep existing compact result fields unchanged.
- [x] Preserve TaskRun success/failure semantics for diagnostics `WARN` and `FAIL`.
- [x] Add focused backend tests for persisted result payload and retry compatibility.

Validation:

```bash
python -m pytest tests/services/test_task_runs_service.py tests/services/test_task_dispatch.py -v
```

## Phase 4: Frontend Integration

### Lane C: Display TaskRun quality diagnostics

- [x] Add defensive parser/helper for `result_json.quality_diagnostics`.
- [x] Render missing, OK, WARN, and FAIL diagnostics in a dedicated TaskRun detail section.
- [x] Keep raw `result_json` fallback visible.
- [x] Add English and Chinese translations for user-visible labels.
- [x] Add or update TaskRun detail page tests.

Validation:

```bash
npm run test:web
```

## Phase 5: Review and Final Verification

- [x] Run focused review for each implementation lane.
- [x] Resolve blocking review findings.
- [x] Run combined backend validation.
- [x] Run `npm run test:web`.
- [x] Run `git diff --stat` and `git status --short --branch`.
- [x] Summarize completed lanes and remaining deferred work.

Summary:

- Lane A implemented ingestion single-fetch. Session-backed ingestion now writes the same serialized snapshot it returns and diagnoses. The duplicate-bar last-write-wins behavior was fixed for `autoflush=False` sessions with an in-memory `(instrument.id, trade_date)` cache.
- Lane B persists ingestion `quality_diagnostics` in worker TaskRun `result_json` while preserving TaskRun technical success/failure semantics, retry lineage, and report lineage.
- Lane C displays TaskRun quality diagnostics on the detail page with defensive parsing, localized missing/OK/WARN/FAIL states, per-instrument issue details, raw JSON fallback, and retry behavior preserved for failed runs.
- Lane D added focused route-handler proxy coverage for daily report generation, including dynamic symbol encoding, query parameter passthrough, and upstream response propagation.
- Reviews approved all lanes after the Lane A duplicate-bar fix. Non-blocking review suggestions for missing diagnostics fallback and failed-run retry display were added as tests.
- Final validation passed: ingestion/data-quality tests, TaskRun/dispatch tests, worker task tests, frontend Vitest suite, Trellis manifest validation, and linter diagnostics.

Remaining deferred work:

- Broader provider error taxonomy refinements remain outside this task.
- Trading calendar-aware quality checks remain outside this task.
- Additional API proxy/client interaction tests can continue in future focused tasks.

Recommended combined validation:

```bash
python -m pytest tests/services/test_ingestion_service.py tests/services/test_data_quality.py -v
python -m pytest tests/services/test_task_runs_service.py tests/services/test_task_dispatch.py -v
npm run test:web
```

## Phase 6: Commit and Push Policy

- [ ] Ask user before committing.
- [ ] Commit reviewed scope only.
- [ ] Push only after explicit user approval.
