# Implementation Plan

## Pre-Development

- [x] Read parent PRD and current task PRD.
- [x] Inspect dashboard, source-readiness, macro, and assistant citation code.
- [x] Review external professional AI/dashboard benchmarks.
- [x] Before code edits, read Trellis backend/frontend specs and shared guides.

## Step 1: Backend Narrative Helper

- [x] Add dashboard narrative fallback/model constants.
- [x] Add prompt/context builder from existing brief sections, citations, diagnostics, and information sources.
- [x] Add optional LLM generation via platform settings and `get_llm_provider()`.
- [x] Validate inline citation IDs against dashboard citations.
- [x] Return additive `dashboard_brief.narrative`.

## Step 2: Backend Tests

- [x] Extend `tests/services/test_market_dashboard_service.py` for deterministic fallback.
- [x] Add LLM success test with monkeypatched provider/settings.
- [x] Add unknown citation fallback test.
- [x] Assert information source gap counts in narrative context.

## Step 3: Frontend Rendering

- [x] Extend dashboard brief payload type in `apps/web/app/[locale]/page.tsx`.
- [x] Render narrative markdown-ish text and model/fallback status.
- [x] Add EN/ZH messages if visible copy is needed.
- [x] Update homepage tests.

## Step 4: Documentation

- [x] Update `README.md`.
- [x] Update `docs/manual/user-guide.md`.
- [x] Mention citation validation, deterministic fallback, and no-investment-advice boundaries.

## Validation

```powershell
pytest tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py
npm run test:web -- --reporter=dot apps/web/app/[locale]/page.test.tsx
npx tsc --noEmit -p apps/web/tsconfig.json
ruff check packages/services/market_dashboard.py tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py
git diff --check
```

Focused validation completed during implementation:

- [x] `pytest tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py`
- [x] `ruff check packages/services/market_dashboard.py tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py`
- [x] `npm run test:web -- --reporter=dot apps/web/app/[locale]/page.test.tsx`
- [x] `npx tsc --noEmit -p apps/web/tsconfig.json`
- [x] `git diff --check`

Full checks before close:

```powershell
pytest
npm run test:web -- --reporter=dot
```

Full validation completed:

- [x] `pytest` (302 passed)
- [x] `npm run test:web -- --reporter=dot` (123 passed)

## Risk Points

- Do not let the LLM invent evidence; citation validation must downgrade unknown citation IDs.
- Do not make homepage require LLM availability.
- Do not turn source readiness gaps into citations.
- Keep edits scoped because the worktree has many pre-existing unrelated changes.
