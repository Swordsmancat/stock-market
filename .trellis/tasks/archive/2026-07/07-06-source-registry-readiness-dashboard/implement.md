# Implementation Plan

## Pre-Development

- [x] Read PRD/design.
- [x] Run `python ./.trellis/scripts/get_context.py --mode packages`.
- [x] Read backend/frontend/shared Trellis specs.
- [x] Confirm dirty worktree and avoid reverting unrelated files.

## Step 1: Backend Source Registry

- [x] Add `packages/services/information_sources.py`.
- [x] Define curated source definitions for macro, valuation, documents, news, reports, and manual seed flows.
- [x] Build readiness from existing DB state without network calls.
- [x] Add focused service tests.

## Step 2: Dashboard Payload Integration

- [x] Add `information_sources` to `packages/services/market_dashboard.py`.
- [x] Update dashboard API tests to assert additive field.
- [x] Preserve existing payload compatibility.

## Step 3: Frontend Dashboard

- [x] Add local payload types in `apps/web/app/[locale]/page.tsx`.
- [x] Render source readiness panel near AI brief/macro indicators.
- [x] Add EN/ZH messages.
- [x] Update homepage test.

## Step 4: Documentation

- [x] Update README.
- [x] Update `docs/manual/user-guide.md`.
- [x] Keep source/legal/freshness boundaries explicit.

## Validation

```powershell
pytest tests/services/test_information_sources_service.py tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py
npm run test:web -- --reporter=dot apps/web/app/[locale]/page.test.tsx
npx tsc --noEmit -p apps/web/tsconfig.json
ruff check packages/services/information_sources.py packages/services/market_dashboard.py tests/services/test_information_sources_service.py tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py
git diff --check
```

Full checks before close:

```powershell
pytest
npm run test:web -- --reporter=dot
```

## Risk Points

- Existing dashboard file has many uncommitted changes. Keep edits focused and do not revert unrelated UI work.
- Source definitions must not claim live/official ingestion until implemented.
- This registry is a readiness layer, not a source license system or scraping engine.

## Validation Results

- [x] `pytest tests/services/test_information_sources_service.py tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py` - passed, 9 tests.
- [x] `npm run test:web -- --reporter=dot apps/web/app/[locale]/page.test.tsx` - passed, 2 tests.
- [x] `npx tsc --noEmit -p apps/web/tsconfig.json` - passed.
- [x] `ruff check packages/services/information_sources.py packages/services/market_dashboard.py tests/services/test_information_sources_service.py tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py` - passed.
- [x] `pytest` - passed, 294 tests.
- [x] `npm run test:web -- --reporter=dot` - passed, 123 tests.
- [x] `git diff --check` - passed; Git emitted line-ending conversion warnings only.
