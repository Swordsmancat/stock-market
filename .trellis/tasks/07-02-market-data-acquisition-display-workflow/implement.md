# Complete market data acquisition and display workflow - Implementation Plan

## Execution rule

This parent task is a product planning and coordination task. Do not directly implement runtime changes in this parent unless a child task explicitly scopes them. Use this parent to preserve the product direction, split work, and verify integration across children.

## Phase 1: Confirm product framing

- [x] Stop the previous route-test automation loop.
- [x] Confirm the current project is an MVP skeleton with several incomplete product flows.
- [x] Distinguish daily historical bars, latest daily bar, and future real-time quote support.
- [x] Audit backend provider, ingestion, market-data, analysis, report, and task-run flows.
- [x] Audit frontend dashboard, instrument detail, reports, task runs, settings, and navigation flows.

## Phase 2: Child task split

Create child tasks in this order unless the user explicitly changes priority.

### 1. Provider settings and readiness visibility

Purpose:

- Make configured provider choice visible and effective.
- Avoid exposing provider secrets.
- Add readiness/capability diagnostics users can understand.

Suggested slug:

- `provider-settings-readiness-visibility`

Validation:

```powershell
python -m pytest tests/api/test_market_data_api.py tests/services/test_market_data_service.py -v
python -m pytest tests/scripts/test_provider_readiness.py -v
npm run test:web -- "apps/web/app/api/settings/route.test.ts"
```

### 2. Single-symbol daily-bar ingestion workflow

Purpose:

- Let users fetch daily bars for a specific symbol without relying on fixture instrument universes.

Suggested slug:

- `single-symbol-daily-bar-ingestion`

Validation:

```powershell
python -m pytest tests/api/test_ingestion_api.py tests/services/test_ingestion_service.py tests/worker/test_tasks.py -v
python -m pytest tests/services/test_database_market_data_service.py -v
```

### 3. No-data and provider-error UX contract

Purpose:

- Stop empty provider results from becoming unclear 500 errors.
- Make backend and frontend no-data states actionable.

Suggested slug:

- `market-data-no-data-error-contract`

Validation:

```powershell
python -m pytest tests/services/test_market_data_service.py tests/api/test_market_data_api.py -v
python -m pytest tests/services/test_report_service.py tests/api/test_reports_api.py tests/api/test_analysis_api.py -v
npm run test:web -- "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx"
```

### 4. Instruments / market-data display page

Purpose:

- Give users a clear page to browse instruments and market-data freshness.

Suggested slug:

- `instruments-market-data-display-page`

Validation:

```powershell
npm run test:web -- "apps/web/app/[locale]/instruments/page.test.tsx"
npm run test:web -- "apps/web/app/[locale]/page.test.tsx"
```

### 5. Instrument detail source/freshness and OHLCV table

Purpose:

- Make single-symbol market data inspectable and trustworthy.

Suggested slug:

- `instrument-detail-source-freshness-table`

Validation:

```powershell
npm run test:web -- "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx"
```

### 6. Task-run feedback from user actions

Purpose:

- Link ingestion, analysis, and report generation actions to their task-run/report results.

Suggested slug:

- `task-run-feedback-from-user-actions`

Validation:

```powershell
npm run test:web -- "apps/web/app/[locale]/actions.test.ts" "apps/web/components/generate-daily-report-button.test.tsx"
npm run test:web -- "apps/web/app/[locale]/task-runs/page.test.tsx" "apps/web/app/[locale]/task-runs/[taskRunId]/page.test.tsx"
```

## Phase 3: Parent integration review

- [ ] Verify each child still aligns with the parent daily-bars product semantics.
- [ ] Verify frontend labels do not promise real-time data unless quote support exists.
- [ ] Verify provider/source/freshness appear in the main display path.
- [ ] Verify user-triggered actions expose a task-run or report follow-up link.
- [ ] Run focused backend and frontend validation for touched layers.
- [ ] Decide whether a second parent wave should design real-time quote support.

## Recommended first implementation child

Start with **Provider settings and readiness visibility**.

Reason:

- It addresses the user's first pain point: data cannot be fetched reliably because users do not know which provider is active or configured.
- It reduces confusion before adding a new display page.
- It can be done without schema migration and without real-network tests.
- It improves both backend correctness and frontend trust.

Second choice, if the user wants visible UI faster:

- **Instruments / market-data display page**, but it will be more useful after provider/source semantics are clearer.

## Stop points

Pause and report if any child task requires:

- database schema migration;
- real provider network tests in CI;
- exposing provider tokens/secrets;
- changing `/market-data/latest` from latest daily bar to quote semantics;
- broad navigation or layout redesign beyond the child task scope.
