# Implementation Plan

## Pre-Development

- [x] Create Trellis child task under the personal information / AI summary parent.
- [x] Review parent PRD/design/implementation plan and existing manual.
- [x] Review current implemented feature evidence from services, frontend copy, README, and prior checks.
- [x] Research information/research platform benchmarks.

## Step 1: Benchmark Research

- [x] Write task research note comparing current implementation with Koyfin, MacroMicro, TradingView, AlphaSense, FRED, World Bank, SEC EDGAR, and Trading Economics.
- [x] Mark current capability as implemented / partial / gap.
- [x] Identify what should not be pursued now.

## Step 2: Manual Update

- [x] Update `docs/manual/user-guide.md` professional comparison and roadmap section.
- [x] Mention current implemented source-to-seed templates and citation-aware dashboard narrative.
- [x] Add next-step plan focused on source aggregation, macro release tracking, daily/weekly AI workflow, and hard-to-find data.

## Step 3: Trellis Follow-Up Plan

- [x] Add a concise P0/P1/P2 plan to the task research note and/or parent planning artifact.
- [x] Keep recommended tasks independently verifiable.
- [x] Do not create implementation children unless the user explicitly selects a next slice.

## Validation

```powershell
git diff --check
```

If runtime files remain unchanged, cite the previously completed validation:

```powershell
pytest
npm run test:web -- --reporter=dot
npx tsc --noEmit -p apps/web/tsconfig.json
ruff check packages/services/information_sources.py tests/services/test_information_sources_service.py tests/api/test_dashboard_api.py
```

## Risk Points

- Do not overclaim live source adapters that are not implemented.
- Do not imply professional platform parity.
- Do not turn source links/templates into AI evidence.
- Do not add new runtime fetches in this docs/planning slice.
