# Dashboard Visual Evidence and WCAG Contrast

## Goal

Close the remaining P0 evidence gap for the frontend UI polish and professional-dashboard audit by capturing durable browser screenshots and explicit light/dark contrast evidence for the main stock-market dashboard surfaces.

## Background

The current code-verifiable UI implementation has already passed TypeScript, frontend tests, backend tests, and browser smoke checks. The remaining open items in `07-03-frontend-ui-polish` are evidence-oriented rather than feature-oriented:

- durable screenshot artifacts are not yet recorded;
- explicit WCAG AA contrast proof for light/dark themes is not yet recorded;
- the professional-dashboard parent task needs reproducible evidence before deciding whether the UI polish task can be archived.

This task is intentionally scoped to evidence collection and documentation updates. It should not broaden into new professional features such as screeners, backtesting, provider SLA dashboards, or workspace persistence.

## Requirements

### 1. Browser screenshot evidence

Capture durable screenshot artifacts for these routes:

- `/zh`
- `/zh/settings`
- `/zh/instruments/AAPL`
- `/zh/watchlist`

Capture at both viewport categories:

- desktop: approximately `1440x900`
- mobile: approximately `390x844`

Each screenshot set must record route, viewport, theme when relevant, timestamp or run context, and whether horizontal overflow/runtime errors were observed.

### 2. Contrast evidence

Run an explicit contrast review for core UI states:

- ticker text and market movement values;
- market-overview table text, muted text, and movement values;
- settings form labels, descriptions, and controls;
- instrument-detail headings and key data values;
- watchlist table/form controls;
- light and dark theme variants where the application supports them.

Record whether each sampled state appears to meet WCAG AA expectations. If exact automated contrast ratios are not available, record manual/browser-observed evidence and mark it as manual evidence rather than automated proof.

### 3. Documentation and Trellis updates

Update the relevant Trellis documents after evidence is captured:

- this task's `implement.md` with execution notes and artifact paths;
- `07-03-frontend-ui-polish` with the evidence closure result;
- `07-05-independent-feature-audit-professional-execution` with parent-task status;
- `07-03-professional-financial-dashboard` only if the evidence changes the professional-dashboard assessment.

### 4. Non-goals

- Do not implement new professional dashboard features in this task.
- Do not claim professional-terminal parity.
- Do not change market data provider semantics.
- Do not convert semantic colors such as error/success/destructive/bid/ask labels into market movement colors.

## Acceptance Criteria

- [x] Screenshot artifacts exist for `/zh`, `/zh/settings`, `/zh/instruments/AAPL`, and `/zh/watchlist` at desktop and mobile widths.
- [x] Evidence notes record whether each tested route had runtime errors or horizontal overflow.
- [x] Light/dark contrast evidence is recorded for representative ticker, table, settings, instrument, and watchlist states.
- [x] Any contrast or layout failure is either fixed if small, or converted into a focused follow-up task if non-trivial.
- [x] `07-03-frontend-ui-polish` is updated to show whether evidence-only items are closed.
- [x] Parent task `07-05-independent-feature-audit-professional-execution` is updated with the P0 evidence result.
- [x] Validation commands and browser conditions are recorded before completion.

## 2026-07-05 Completion Evidence

- The browser evidence pass covered all required route/viewport pairs.
- The original browser-tool screenshots were regenerated into `evidence/screenshots/*.png` with a local headless Chromium-family browser and a non-empty-file check.
- Contrast sampling found one small defect: neutral ticker movement text on the black ticker surface was below normal-text AA in light theme.
- The defect was fixed by rendering flat or missing ticker movement values with `text-gray-300` on the black ticker surface.
- `apps/web/components/market-ticker.test.tsx` now covers the neutral ticker movement class.
- Focused test, frontend type-check, full web test, lint diagnostics, and diff whitespace checks passed.

## Out of Scope

- Provider production validation.
- Level-2, fund-flow, screener, backtesting, workspace, or AI corpus implementation.
- Git commit, push, or archive unless explicitly requested after validation.
