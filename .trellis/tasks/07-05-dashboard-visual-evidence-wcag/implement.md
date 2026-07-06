# Dashboard Visual Evidence and WCAG Contrast - Implementation Plan

## Current phase

In progress. Evidence capture and the small contrast fix were completed on 2026-07-05.

## Execution checklist

### 1. Environment check

- [x] Check whether a Next.js dev server is already running.
- [x] If no healthy server exists, start one and wait until it serves `http://127.0.0.1:3000/zh` or the configured local URL.
- [x] Record the server URL and viewport sizes used.

### 2. Screenshot capture

- [x] Capture `/zh` desktop screenshot.
- [x] Capture `/zh` mobile screenshot.
- [x] Capture `/zh/settings` desktop screenshot.
- [x] Capture `/zh/settings` mobile screenshot.
- [x] Capture `/zh/instruments/AAPL` desktop screenshot.
- [x] Capture `/zh/instruments/AAPL` mobile screenshot.
- [x] Capture `/zh/watchlist` desktop screenshot.
- [x] Capture `/zh/watchlist` mobile screenshot.

### 3. Browser observations

For each route and viewport, record:

- [x] page loaded successfully;
- [x] no runtime-error text;
- [x] no visible document/body horizontal overflow;
- [x] key route-specific content is present;
- [x] any console errors observed during the pass.

### 4. Contrast evidence

- [x] Sample light-theme text/movement/control contrast states.
- [x] Sample dark-theme text/movement/control contrast states if theme switching is available in the browser session.
- [x] Record exact ratios when available; otherwise explicitly label the result as manual/browser evidence.
- [x] Convert any clear failure into either a small fix or a follow-up task.

### 5. Documentation updates

- [x] Create or update `evidence/visual-evidence.md`.
- [x] Create or update `evidence/contrast-evidence.md`.
- [x] Update `07-03-frontend-ui-polish` with evidence closure status.
- [x] Update parent task `07-05-independent-feature-audit-professional-execution` with P0 result.
- [x] Update `07-03-professional-financial-dashboard` if the evidence changes its assessment.

## 2026-07-05 Execution Notes

Artifacts:

- `evidence/visual-evidence.md`
- `evidence/contrast-evidence.md`
- `evidence/browser-observations.json`
- `evidence/contrast-samples.json`
- `evidence/screenshots/*.png`

The screenshot files were regenerated into `evidence/screenshots/` using a local headless Chromium-family browser. The generation command failed on missing or zero-byte output, and completed successfully.

Small fix:

- `apps/web/components/market-ticker.tsx` uses `text-gray-300` for flat or missing movement values in the black ticker, replacing the previous global muted color that measured below normal-text AA in light theme.
- `apps/web/components/market-ticker.test.tsx` covers the neutral ticker movement class.

Observed browser status:

- `/zh`, `/zh/settings`, `/zh/instruments/AAPL`, and `/zh/watchlist` loaded at `1440x900` and `390x844`.
- No tested route showed document/body horizontal overflow.
- No tested route showed runtime-error text.
- No browser console errors were captured.
- `/zh/settings` exposed both `china` and `international` market-color choices and the `tushare_http_url` field.

Contrast status:

- Final sampled light/dark states passed WCAG AA for their text size.
- The instrument large movement value passed as large text (`3.30:1` in light theme at `24px` bold); do not reuse that exact green/red treatment for smaller text without rechecking contrast.

Validation run:

```powershell
npx vitest run "apps/web/components/market-ticker.test.tsx" --reporter=dot
# 1 test file passed, 2 tests passed

npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0
# passed

npm run test:web -- --reporter=dot
# 33 test files passed, 111 tests passed

git diff --check -- .trellis/tasks/07-05-dashboard-visual-evidence-wcag .trellis/tasks/07-03-frontend-ui-polish .trellis/tasks/07-05-independent-feature-audit-professional-execution .trellis/tasks/07-03-professional-financial-dashboard apps/web/components/market-ticker.tsx apps/web/components/market-ticker.test.tsx
# passed; Windows CRLF conversion warnings only
```

## Validation commands

Evidence-only work may not require the full test suite unless code is changed. If code changes are made, run:

```powershell
npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0
npm run test:web -- --reporter=dot
git diff --check
```

If only documentation/evidence files change, run:

```powershell
git diff --check -- .trellis/tasks/07-05-dashboard-visual-evidence-wcag .trellis/tasks/07-03-frontend-ui-polish .trellis/tasks/07-05-independent-feature-audit-professional-execution .trellis/tasks/07-03-professional-financial-dashboard
```

## Completion decision

After evidence is recorded, decide whether `07-03-frontend-ui-polish` can be archived or whether a remaining contrast/layout defect must become a new focused task.
