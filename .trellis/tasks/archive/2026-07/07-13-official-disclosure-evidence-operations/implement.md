# Implementation plan

## Ordered checklist

1. Add configuration and backend operations service for eligible watchlist selection, coverage aggregation, bounded sequential refresh/ingestion, progress, and sanitized diagnostics.
2. Add batch request/active-run dedupe endpoints to the official-disclosure router.
3. Register TaskRun dispatch and Celery worker execution with progress/final result handling.
4. Add backend service, API, dispatch, and worker tests for eligibility, limits, sequence, delay, partial failure, no-data, dedupe, and payload safety.
5. Add same-origin single-ingest and watchlist-batch proxy routes with tests.
6. Add localized Evidence Center disclosure operations panel and server loader with component/page tests.
7. Update executable backend/frontend specs, README, and user guide.
8. Run focused Ruff/Mypy/pytest, web lint/type/test, full repository pytest, and diff checks.

## Validation commands

```powershell
python -m pytest -q tests/services/test_official_disclosure_operations.py tests/api/test_official_disclosures_api.py tests/services/test_task_dispatch.py tests/worker/test_ingestion_tasks.py
python -m ruff check packages/services/official_disclosure_operations.py apps/api/routers/official_disclosures.py packages/services/task_dispatch.py apps/worker/tasks/ingestion.py
python -m mypy --follow-imports=skip --ignore-missing-imports packages/services/official_disclosure_operations.py apps/api/routers/official_disclosures.py apps/worker/tasks/ingestion.py
pnpm --dir apps/web test -- --run
pnpm --dir apps/web lint
pnpm --dir apps/web typecheck
python -m pytest -q
git diff --check
```

## Review gates

- No full-universe fallback when the watchlist is empty.
- No parallel CNINFO calls or duplicate active batch dispatch.
- No absolute storage path, raw provider payload, or exception detail leakage.
- Metadata and content citation boundaries remain visually and structurally distinct.
- Partial failure counters equal item outcomes and successful evidence remains committed.
- Existing Evidence Center sections and task-run navigation remain intact.

## Risk and rollback points

- CNINFO pressure: bound symbols/documents, delay every external operation, and run sequentially.
- Long-running tasks: update heartbeat after each unit and keep a small default maximum.
- Large Evidence Center payload: aggregate in SQL and cap returned disclosure rows.
- Frontend page size: isolate interactive logic in a dedicated component.

## Validation results

- Changed backend Ruff: passed.
- Focused backend Mypy: passed.
- Focused backend operations/API/dispatch/worker suite: 46 passed.
- Full backend suite: 634 passed.
- Focused Evidence Center/component/proxy suite: 7 passed.
- Full Web suite: 209 passed across 71 files.
- Web TypeScript no-emit check: passed.
- `git diff --check`: passed with repository line-ending warnings only.
- Browser acceptance: the new Evidence Center panel rendered in the running frontend with
  correct localized actions and citation boundaries. Because the existing port-8000 process
  was intentionally not restarted, its missing new route produced the designed explicit
  failed-load state without affecting the rest of the page.
