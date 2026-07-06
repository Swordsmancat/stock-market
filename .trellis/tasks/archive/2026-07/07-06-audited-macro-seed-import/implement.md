# Implementation Plan

## Pre-Development

- [x] Read parent PRD and completed source-readiness task artifacts.
- [x] Run `python ./.trellis/scripts/get_context.py --mode packages`.
- [x] Read backend Trellis specs and shared code-reuse guide.
- [x] Confirm dirty worktree and avoid reverting unrelated files.

## Step 1: Service Parser and Validator

- [x] Add import result/error dataclasses to `packages/services/market_indicators.py`.
- [x] Parse JSON array/object and CSV `components_json`.
- [x] Validate required fields, decimal/date parsing, components object shape, and audit metadata keys.
- [x] Validate indicator definitions exist after seeding curated definitions.
- [x] Ensure import validates all rows before any upsert/commit.

## Step 2: Script Entry

- [x] Add `scripts/import_market_indicator_seeds.py`.
- [x] Use the configured `SessionLocal` only in the CLI boundary.
- [x] Print concise success/failure output and return nonzero for validation errors.

## Step 3: Tests

- [x] Extend `tests/services/test_market_indicators_service.py` for JSON, CSV, bad metadata, unknown code, and all-or-nothing behavior.
- [x] Add `tests/scripts/test_import_market_indicator_seeds.py` with monkeypatched session factory.

## Step 4: Documentation

- [x] Update `README.md`.
- [x] Update `docs/manual/user-guide.md`.
- [x] Keep no-live-feed/no-scraping wording explicit.

## Validation

```powershell
pytest tests/services/test_market_indicators_service.py tests/scripts/test_import_market_indicator_seeds.py
pytest tests/services/test_information_sources_service.py tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py
ruff check packages/services/market_indicators.py scripts/import_market_indicator_seeds.py tests/services/test_market_indicators_service.py tests/scripts/test_import_market_indicator_seeds.py
git diff --check
```

Before final close, also run:

```powershell
pytest
```

## Risk Points

- `market_indicators.py` already has user-facing no-data semantics; do not weaken them by accepting unaudited rows.
- Existing worktree has many unrelated frontend/backend changes; touch only the files required for this slice.
- The script is intentionally a write tool, so tests must avoid the real configured database.

## Spec Update

- [x] Added `.trellis/spec/backend/market-indicator-seed-import-contract.md`.
- [x] Linked the new backend contract from `.trellis/spec/backend/index.md`.

## Validation Results

- [x] `pytest tests/services/test_market_indicators_service.py tests/scripts/test_import_market_indicator_seeds.py` - passed, 11 tests.
- [x] `pytest tests/services/test_market_indicators_service.py tests/scripts/test_import_market_indicator_seeds.py tests/services/test_information_sources_service.py tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py` - passed, 20 tests.
- [x] `ruff check packages/services/market_indicators.py scripts/import_market_indicator_seeds.py tests/services/test_market_indicators_service.py tests/scripts/test_import_market_indicator_seeds.py` - passed.
- [x] `git diff --check` - passed; Git emitted line-ending conversion warnings only.
- [x] `pytest` - passed, 300 tests.
- [x] `npm run test:web -- --reporter=dot` - passed, 123 tests. The hot-sectors route test intentionally logs a simulated `network down` error.
- [x] `npx tsc --noEmit -p apps/web/tsconfig.json` - passed.

## Commit Status

- [ ] Not committed in this session because the worktree contains many pre-existing unrelated edits, including overlapping files from earlier Trellis slices.
