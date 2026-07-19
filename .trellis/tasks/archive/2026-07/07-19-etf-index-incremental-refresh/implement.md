# ETF and Index Incremental Refresh Implementation Plan

## Ordered Work

- [x] Add failing service tests for full seed, overlap, current skip, source lock, result metadata, and attempted-only provider-wide failure.
- [x] Extend the coordinator factory with exact ETF/index source selection and focused routing tests.
- [x] Add one bounded refresh-state projection and per-symbol window selection to the pipeline.
- [x] Preserve progress, pacing, checkpoint, sanitization, and backward-compatible worker/API inputs.
- [x] Map scheduled worker delivery to incremental mode and manual/retry delivery to full-window mode.
- [x] Run focused provider/ingestion/pipeline/worker/API tests and Ruff.
- [x] Run the full Python and Web suites, TypeScript, JSON, and diff validation.
- [x] Update the executable ingestion contract and runbook.
- [x] Perform a bounded live rerun and verify coherent provenance and service health.
- [x] Complete final verification and prepare the scoped commit/archive delivery.

## Validation Commands

```powershell
pytest tests/services/test_cn_fund_index_pipeline.py tests/services/test_ingestion_service.py
pytest tests/worker/test_tasks.py tests/worker/test_celery_schedule.py tests/api/test_ingestion_api.py
ruff check packages/services tests/services tests/worker tests/api
pytest -q
npm.cmd run test:web
npx.cmd tsc --noEmit -p apps/web/tsconfig.json
python ./.trellis/scripts/task.py validate 07-19-etf-index-incremental-refresh
```

## Risk and Rollback Points

- Cohort corruption: exact-source locks prevent cross-adjustment fallback for existing instruments.
- N+1 queries: one bounded latest-row projection covers every selected instrument.
- False provider-wide failure: only attempted symbols participate; current skips do not.
- Source schema drift: unknown stored sources fail visibly and never silently switch.
- Runtime regression: a bounded real rerun must preserve 100% ETF/index coverage and coherent per-instrument provenance.
