# Parallel Backlog Execution Plan

## Phase 1: State Synchronization

- [x] Review active Trellis tasks and decide which completed tasks should be archived.
- [x] Update or annotate completed plan documents so they no longer appear as fully pending work.
- [x] Confirm whether `00-bootstrap-guidelines` is complete or requires a separate follow-up.
- [x] Validate git status after workflow-state edits.

## Phase 2: Parallel Implementation Candidates

After Phase 1, launch only non-overlapping lanes.

### Candidate Lane B: Backend indicator/provider resilience

- [x] Add tests for empty bars, insufficient indicator data, and provider failure paths.
- [x] Implement graceful responses or explicit errors for those cases.
- [x] Validate with focused backend tests.

Suggested validation:

```bash
python -m pytest tests/services/test_market_data_service.py tests/api/test_market_data_api.py tests/api/test_market_data_db_api.py -v
```

### Candidate Lane C: Data quality integration

- [x] Decide whether quality diagnostics should be attached to ingestion result or TaskRun result first.
- [x] Add focused tests around ingestion result diagnostics.
- [x] Wire the existing pure data quality service into the selected path.

Suggested validation:

```bash
python -m pytest tests/services/test_ingestion_service.py tests/services/test_data_quality.py -v
```

### Candidate Lane D: Frontend error/i18n cleanup

- [x] Identify high-value hardcoded text and formatting issues.
- [x] Add or update translations.
- [x] Improve at least one key page to distinguish empty state from error state.

Suggested validation:

```bash
npm run test:web
```

### Candidate Lane E: API proxy/client interaction tests

Status: proxy-test scope completed by `07-02-add-deferred-api-proxy-tests`. Additional client form or polling behavior coverage remains a future testing backlog item.

- [x] Add tests for one high-value API route proxy.
- [ ] Add tests for one high-value client form or polling behavior. Deferred to future proxy/client interaction coverage.

Suggested validation:

```bash
npm run test:web
```

## Phase 3: Reviews

- [x] Run one spec review subagent per implementation lane.
- [x] Run one quality review subagent per implementation lane.
- [x] Resolve blocking review findings before combining lanes.

## Phase 4: Final Verification

- [x] Run focused backend tests touched by implementation lanes.
- [x] Run `npm run test:web` if frontend files changed.
- [x] Run `python scripts/dev_health_check.py` only if local services are available; otherwise record environment limitation.
- [x] Review `git diff --stat` and `git status --short --branch`.

## Phase 5: Commit Policy

- [x] Ask the user before creating any commit.
- [x] Commit only reviewed files for the approved scope.
- [x] Do not push unless the user explicitly requests it.
