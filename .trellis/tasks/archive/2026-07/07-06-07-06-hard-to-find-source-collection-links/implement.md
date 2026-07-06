# Implementation Plan

## Pre-Development

- [x] Create Trellis task.
- [x] Draft PRD and design.
- [x] Read backend/frontend specs and shared guides before code edits.

## Step 1: Backend Registry Metadata

- [x] Extend source definition model with collection links, collection note, and citation policy.
- [x] Add official/legal links for FRED rates/inflation/liquidity, PBOC/manual CN M2, Buffett manual valuation components, generated reports, stored news, future SEC/documents, and user seed files where appropriate.
- [x] Keep source readiness status/evidence logic unchanged.

## Step 2: Backend Tests

- [x] Cover official macro collection links.
- [x] Cover manual valuation collection guidance.
- [x] Cover future document citation policy.

## Step 3: Frontend Rendering

- [x] Extend homepage source readiness item type.
- [x] Render collection note, citation policy, and external source links.
- [x] Add EN/ZH i18n strings.
- [x] Update homepage test fixture/assertions.

## Step 4: Documentation

- [x] Update README.
- [x] Update `docs/manual/user-guide.md`.
- [x] Mention no scraping, no automatic ingestion, and citation boundary.

## Validation

```powershell
pytest tests/services/test_information_sources_service.py tests/api/test_dashboard_api.py
npm run test:web -- --reporter=dot apps/web/app/[locale]/page.test.tsx
npx tsc --noEmit -p apps/web/tsconfig.json
ruff check packages/services/information_sources.py tests/services/test_information_sources_service.py tests/api/test_dashboard_api.py
git diff --check
```

Focused validation results:

- [x] `pytest tests/services/test_information_sources_service.py tests/api/test_dashboard_api.py`
- [x] `npm run test:web -- --reporter=dot apps/web/app/[locale]/page.test.tsx`
- [x] `npx tsc --noEmit -p apps/web/tsconfig.json`
- [x] `ruff check packages/services/information_sources.py tests/services/test_information_sources_service.py tests/api/test_dashboard_api.py`
- [x] `git diff --check` (passed; Git reported CRLF normalization warnings only)

Full checks before close:

```powershell
pytest
npm run test:web -- --reporter=dot
```

Full validation results:

- [x] `pytest` (305 passed)
- [x] `npm run test:web -- --reporter=dot` (37 files / 123 tests passed; expected stderr from hot-sectors error-path test)

## Risk Points

- Do not represent links as evidence citations.
- Do not imply official APIs are configured.
- Do not scrape or fetch external sources in tests.
- Keep edits scoped because the worktree already has many unrelated changes.
