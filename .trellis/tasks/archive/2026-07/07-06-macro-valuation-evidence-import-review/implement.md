# Implementation Plan

## Current Phase

Execution complete; quality verification and finish-work steps are in progress.

## Pre-Development

- [x] Confirm task direction: personal macro/valuation evidence import and review workflow.
- [x] Confirm browser file upload is in scope alongside pasted JSON/CSV content.
- [x] Inspect existing seed importer, tests, database model, Evidence Center route, API router patterns, frontend proxy patterns, cache helper, and Trellis specs.
- [x] Write PRD/design/implementation plan.

## Step 1: Backend Content Parser And Preview Service

- [x] Refactor `packages/services/market_indicators.py` so JSON/CSV row parsing can be driven by file path or raw content.
- [x] Keep `parse_market_indicator_observation_seed_file(...)` and `import_market_indicator_observation_seed_file(...)` backward compatible.
- [x] Add content-format inference from explicit format, filename extension, or content shape.
- [x] Add preview service that validates rows without writes and returns row-level status/errors.
- [x] Add insert/update detection using existing indicator definitions and observations.
- [x] Add focused service tests for valid JSON, valid CSV, invalid rows, unknown codes, no-write preview, and update detection.

## Step 2: Backend Import API

- [x] Add FastAPI router for `/market-indicators/seeds/preview` and `/market-indicators/seeds/import`.
- [x] Register the router in `apps/api/main.py`.
- [x] Return HTTP 200 for preview validation feedback, HTTP 422 for invalid confirmed import, and HTTP 409 for missing overwrite acknowledgement.
- [x] Preserve all-or-nothing confirmed import behavior.
- [x] Clear market-overview cache after successful import.
- [x] Add API tests with SQLite session overrides.

## Step 3: Next.js Proxy And Client Workflow

- [x] Add same-origin route proxies for preview/import if the client component calls `/api/...`.
- [x] Add a client component for paste + file-picker seed review.
- [x] Read selected `.json`/`.csv` file content into the review text area without storing the raw file.
- [x] Render preview summary, row table, errors, insert/update badges, and citation boundary.
- [x] Require overwrite acknowledgement when update rows are present.
- [x] Trigger confirmed import and show success/failure state.
- [x] Revalidate or refresh the Evidence Center after successful import.
- [x] Add/update English and Chinese translations.
- [x] Add frontend tests for file-read/paste preview, invalid preview, update acknowledgement, successful import, and proxy forwarding.

## Step 4: Documentation

- [x] Update `docs/manual/user-guide.md` with the import/review workflow.
- [x] Update `docs/runbooks/developer-maintenance.md` with focused validation commands.
- [x] Mention CLI import remains available.
- [x] Document that uploaded files are read for content only and are not stored.

## Validation Commands

Focused backend:

```powershell
python -m pytest tests/services/test_market_indicators_service.py tests/api/test_market_indicators_api.py -q
```

Focused frontend:

```powershell
npx vitest run "apps/web/app/[locale]/evidence/page.test.tsx" "apps/web/components/evidence-seed-import-review.test.tsx" "apps/web/app/api/market-indicators/seeds/preview/route.test.ts" "apps/web/app/api/market-indicators/seeds/import/route.test.ts" --reporter=dot
npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0
```

Compatibility:

```powershell
python -m pytest tests/scripts/test_import_market_indicator_seeds.py tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py -q
npm run test:web -- --reporter=dot
git diff --check
```

## Validation Results

- [x] `python -m pytest tests/services/test_market_indicators_service.py tests/api/test_market_indicators_api.py tests/scripts/test_import_market_indicator_seeds.py tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py -q` -> 28 passed.
- [x] `npx vitest run "apps/web/app/[locale]/evidence/page.test.tsx" "apps/web/components/evidence-seed-import-review.test.tsx" "apps/web/app/api/market-indicators/seeds/preview/route.test.ts" "apps/web/app/api/market-indicators/seeds/import/route.test.ts" --reporter=dot` -> 11 passed.
- [x] `npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0` -> passed.
- [x] `npm run test:web -- --reporter=dot` -> 41 files / 134 tests passed.
- [x] `node -e "JSON.parse(...en.json); JSON.parse(...zh.json)"` -> messages ok.
- [x] `python -m py_compile packages\services\market_indicators.py apps\api\routers\market_indicators.py` -> passed.
- [x] `ruff check packages/services/market_indicators.py apps/api/routers/market_indicators.py tests/services/test_market_indicators_service.py tests/api/test_market_indicators_api.py` -> passed.
- [x] `git diff --check` -> passed.

## Review Gate

- [x] User reviews PRD, design, and implementation plan.
- [x] If approved, run `python ./.trellis/scripts/task.py start .trellis/tasks/07-06-macro-valuation-evidence-import-review`.

## Risk Points

- Keep preview non-mutating.
- Do not create a second audit validation contract.
- Do not persist raw uploaded files.
- Do not allow silent overwrites of existing observations.
- Do not make source links/templates into AI citations.
- Do not expand into scraping, scheduled ingestion, or trading advice.
