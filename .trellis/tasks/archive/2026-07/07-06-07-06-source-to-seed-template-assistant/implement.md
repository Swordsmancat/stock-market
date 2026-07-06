# Implementation Plan

## Pre-Development

- [x] Create Trellis task.
- [x] Draft PRD.
- [x] Draft design.
- [x] Read backend/frontend specs and shared guides before code edits.
- [x] Incorporate read-only feedback from Hegel/Avicenna if it returns before implementation.

## Step 1: Backend Seed Template Contract

- [x] Add `SourceSeedTemplate` payload model.
- [x] Add optional `seed_template` to `SourceDefinition`.
- [x] Add templates for FRED rates/inflation/liquidity, PBOC China M2, Buffett components, and generic user seed files.
- [x] Keep readiness status/evidence logic unchanged.

## Step 2: Backend Tests

- [x] Cover FRED rates template target codes, placeholders, import command, and review checklist.
- [x] Cover Buffett component template and citation boundary.
- [x] Cover generic user seed-file template.
- [x] Cover dashboard API additive payload.
- [x] Assert dashboard brief citations do not include source/template IDs.

## Step 3: Frontend Rendering

- [x] Extend homepage source readiness item type.
- [x] Render seed-template label, target codes, required fields, import command, review checklist, JSON preview, CSV preview, and citation boundary.
- [x] Add EN/ZH i18n strings.
- [x] Update homepage test fixture/assertions.

## Step 4: Documentation and Spec

- [x] Update README.
- [x] Update `docs/manual/user-guide.md`.
- [x] Update citation/source-readiness contract spec.
- [x] Mention templates are guidance only; no scraping, no automatic ingestion, no advice, no citation until imported.

## Validation

```powershell
pytest tests/services/test_information_sources_service.py tests/api/test_dashboard_api.py
npm run test:web -- --reporter=dot apps/web/app/[locale]/page.test.tsx
npx tsc --noEmit -p apps/web/tsconfig.json
ruff check packages/services/information_sources.py tests/services/test_information_sources_service.py tests/api/test_dashboard_api.py
git diff --check
```

Full checks before close:

```powershell
pytest
npm run test:web -- --reporter=dot
```

## Risk Points

- Do not generate real-looking macro values.
- Do not fetch source links or external APIs.
- Do not represent template rows as evidence citations.
- Do not imply the import command ran.
- Keep edits scoped because the worktree already has many unrelated changes.
