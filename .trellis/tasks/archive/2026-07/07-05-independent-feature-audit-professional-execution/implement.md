# Independent Feature Audit and Professional Benchmark Execution - Implementation Plan

## Current phase

Audit execution complete for the requested scope. P0 evidence closure was executed through child task `07-05-dashboard-visual-evidence-wcag`; the remaining professional gaps are planned follow-up work, not blockers for this audit.

## Completed planning setup

- Created parent task `07-05-independent-feature-audit-professional-execution` for this independent audit/execution request.
- Loaded available Trellis context from the current repository state.
- Reviewed existing active task evidence from `07-03-frontend-ui-polish` and `07-03-professional-financial-dashboard`.
- Captured current status: MVP code-verifiable work is broadly complete; professional-terminal parity remains incomplete and should be split into focused follow-up tasks.

## Ordered execution checklist

### 1. Parent task convergence

- [x] Finalize `prd.md` with goal, scope, requirements, acceptance criteria, status assessment, and open questions.
- [x] Finalize `design.md` with task map, status classification model, benchmark dimensions, and safety constraints.
- [x] Finalize `implement.md` with next execution steps and validation plan.
- [x] Link or map existing active tasks under this parent when appropriate.

### 2. Recommended first execution slice: P0 evidence closure

- [x] Create or reuse a focused child task for dashboard visual evidence and WCAG contrast proof.
- [x] Start the child task only after approval.
- [x] Capture durable screenshots for `/zh`, `/zh/settings`, `/zh/instruments/AAPL`, and `/zh/watchlist` at desktop and mobile widths.
- [x] Run explicit light/dark contrast checks for movement colors, table text, ticker text, and key controls.
- [x] Update `07-03-frontend-ui-polish` with durable evidence.
- [x] Decide whether `07-03-frontend-ui-polish` can be archived after evidence closure.

### 2.1 P0 evidence closure result

Completed under child task `07-05-dashboard-visual-evidence-wcag`.

- Screenshot evidence: `07-05-dashboard-visual-evidence-wcag/evidence/visual-evidence.md`
- Contrast evidence: `07-05-dashboard-visual-evidence-wcag/evidence/contrast-evidence.md`
- Raw browser observations: `07-05-dashboard-visual-evidence-wcag/evidence/browser-observations.json`
- Raw contrast samples: `07-05-dashboard-visual-evidence-wcag/evidence/contrast-samples.json`

One small code fix was required and completed: black ticker neutral movement values now use `text-gray-300` because the previous muted text was below normal-text AA in light theme. The focused regression test passed.

Current decision: `07-03-frontend-ui-polish` is archive-ready from an implementation/evidence perspective. The parent audit remains open only if the next selected work is professional benchmark execution or task archival/commit workflow.

### 3. Professional benchmark execution

- [x] Ensure the professional benchmark plan references Yahoo Finance, TradingView, Bloomberg/Koyfin/AlphaSense, Eastmoney/Tonghuashun/ifind, and Futu/Moomoo-style workflows.
- [x] Convert each unimplemented professional gap into a focused Trellis task only when it is selected for execution.
- [x] Keep provider-trust and no-fabrication tasks ahead of convenience UI tasks when a claim depends on data reliability.

### 4. Validation commands

Use focused commands when implementation changes are made:

```powershell
npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0
npm run test:web -- --reporter=dot
pytest
git diff --check
```

Use browser smoke for visual/evidence work:

- `/zh` desktop and mobile.
- `/zh/settings` desktop and mobile.
- `/zh/instruments/AAPL` desktop and mobile.
- `/zh/watchlist` desktop and mobile.

## Risk points

- The working tree is already dirty; preserve unrelated changes and avoid reverting user work.
- Existing active tasks contain extensive evidence. Do not duplicate or contradict them.
- Professional website parity is a multi-task roadmap, not a single cleanup item.
- Browser/WCAG evidence can fail because of theme, viewport, or generated chart rendering; record exact conditions.

## Recommended next decision

The requested audit/execution scope is complete. Optional next steps are task archival/commit workflow, or starting a focused child task for one selected professional gap such as provider validation, screener/watchlist workflows, workspace persistence, backtesting, or portfolio/risk analytics.
