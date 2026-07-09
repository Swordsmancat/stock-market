# 前端整站重新美化 - Implement

## Ordered Checklist

- [x] Before coding, load `trellis-before-dev` and re-read relevant frontend specs.
- [x] Re-open `prd.md` and confirm the chosen visual direction remains professional terminal density first.
- [x] Capture a quick baseline inventory of routes and obvious visual inconsistencies.
- [x] Update global design tokens in `apps/web/app/globals.css` and Tailwind usage without breaking shadcn variables.
- [x] Polish global shell components: top nav, sidebar nav, mobile nav, breadcrumbs/status placement.
- [x] Upgrade `FinancialPageHeader` or add a closely related shared header component for all core pages.
- [x] Migrate Dashboard, Watchlist, Settings, and Instrument Detail to the final shared visual language.
- [x] Migrate Instruments, Reports, Alerts, Task Runs, and Portfolios to unified table/panel/header patterns.
- [x] Migrate AI Research, Evidence, Report Detail, and Task Run Detail with special attention to dense research content and long text.
- [x] Normalize form controls, status badges, action buttons, empty/error/loading states, and chart panels.
- [x] Update `apps/web/messages/en.json` and `apps/web/messages/zh.json` together for any new text.
- [x] Update affected page/component tests.
- [x] Run static and automated validation.
- [x] Run browser smoke on representative desktop and mobile routes.
- [x] Review whether any new frontend convention should be captured in `.trellis/spec/frontend/`.

## Implementation Notes

- Global tokens, Tailwind semantic colors, shadcn-style UI primitives, shell navigation, global search, and shared page header were shifted toward a compact financial-terminal visual system.
- Core routes now use `FinancialPageHeader`/`FinancialDashboardHero` consistently across Dashboard, Instruments, AI Research, Evidence, Watchlist, Portfolios, Reports, Report Detail, Alerts, Task Runs, Task Run Detail, Settings, and Instrument Detail.
- List/detail pages were adjusted to avoid duplicate exact text that made behavior tests brittle after adding header metrics and badges.
- New Task Runs header metric labels were added to both `apps/web/messages/en.json` and `apps/web/messages/zh.json`.
- Existing `.trellis/spec/frontend/component-guidelines.md` already documents the dense financial page header convention.
- Updated `.trellis/spec/frontend/quality-guidelines.md` with the `next-intl` raw JSON message gotcha after browser smoke exposed an ICU malformed-message failure on the Evidence route.

### Second Wave: TradingView-Inspired Market Workspace

- User feedback after the first pass: the site still looked too similar to the previous UI.
- Updated the direction to a TradingView-inspired but original chart-first market workspace.
- Added `MarketWorkspaceHero` for the dashboard first viewport: market strip, primary chart panel, watchlist board, core market rows, and compact research actions.
- Shifted the shell from terminal-grid styling to a cleaner charting-platform workspace with blue active states and light surfaces.
- Updated `MarketTicker` from a dark terminal strip/select control to a contained market-board strip with segmented filters and no document-level horizontal overflow.
- Added localized strings for the new dashboard workspace and ticker filters in both English and Chinese.
- Updated focused tests for the dashboard and ticker component.

### Third Wave: Curated Homepage Correction

- User corrected the core need: the homepage should not collect every feature. Deep workflows must live in their owning modules.
- Replaced the dashboard workspace hero with a compact curated market overview: top index ticker, core US/A-share index cards, macro favorites, hot sectors, latest news sentiment, and compact important status.
- Removed homepage rendering and data loading for AI research brief, information-source readiness, research recommendations, comparison tool, followed K-line table, daily report, AI stock report, technical indicators, fundamentals, and homepage action forms.
- Deleted the obsolete `apps/web/components/market-workspace-hero.tsx` component.
- Updated localized homepage copy and settings copy so macro favorites are described as homepage macro-watchlist items, not AI-brief-adjacent items.
- Updated `apps/web/app/[locale]/page.test.tsx` to assert the curated homepage surface and explicitly guard against the removed deep homepage modules.

### Fourth Wave: Submodule Placement Contract

- User clarified that deep modules removed from the homepage still need to appear in their owning submodules rather than disappear from the product.
- Confirmed existing homes for AI research, source/evidence workflows, reports, task-run details, and instrument K-line/depth workflows.
- Added the comparison workflow to the Instruments module with localized labels and comparison daily-bar fetching for visible instruments.
- Extended Instrument Detail data loading with optional technical indicators, fundamentals, latest news sentiment, latest daily report, and recent daily-report history. Optional failures degrade to empty fallback payloads while bars remain the hard failure boundary.
- Updated Instrument Detail rendering so stock reports, report history, technical indicators, fundamentals, and news sentiment live on the instrument submodule instead of the homepage.
- Updated route/page/component tests so the homepage stays curated while Instruments and Instrument Detail retain their deeper analytical workflows.

## Validation Evidence

- `git diff --check` passed with Git CRLF warnings only.
- `npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0` passed.
- Focused Vitest for modified page tests passed: 10 files, 25 tests.
- `npm run test:web -- --reporter=dot` passed: 50 files, 158 tests.
- Browser smoke passed on 44 route/viewport combinations: `/zh`, `/zh/instruments`, `/zh/instruments/AAPL`, `/zh/ai-research`, `/zh/evidence`, `/zh/watchlist`, `/zh/portfolios`, `/zh/reports`, `/zh/alerts`, `/zh/task-runs`, `/zh/settings` across 390x844, 768x1024, 1024x768, and 1440x900. No page errors or horizontal document overflow were detected.
- Second-wave focused validation passed: `npx vitest run "apps/web/app/[locale]/page.test.tsx" apps/web/components/market-ticker.test.tsx --reporter=dot` passed 2 files / 4 tests.
- Second-wave final validation passed: `git diff --check`, `npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0`, `npm run test:web -- --reporter=dot` (50 files / 158 tests), and browser smoke across 44 route/viewport combinations. Browser smoke ignored only ordinary missing-resource 404 console noise and found no real page errors or horizontal document/body overflow.
- Third-wave focused validation passed: `npx vitest run "apps/web/app/[locale]/page.test.tsx" --reporter=dot` passed 1 file / 2 tests.
- Third-wave final validation passed: `git diff --check` passed with Git CRLF warnings only; `npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0` passed; `npm run test:web -- --reporter=dot` passed 50 files / 158 tests.
- Third-wave browser smoke used headless Chrome through DevTools Protocol because `playwright` is not installed in the repo. It passed 44 route/viewport combinations with no page errors, empty renders, or document/body horizontal overflow.
- Fourth-wave focused route validation passed: `npx vitest run "apps/web/app/api/instruments/[symbol]/route.test.ts" --reporter=dot` passed 1 file / 7 tests.
- Fourth-wave final automated validation passed: `npm run test:web -- --reporter=dot` passed 50 files / 158 tests; `npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0` passed; `git diff --check` passed with Git CRLF warnings only.

## Validation Commands

```powershell
git diff --check
npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0
npm run test:web -- --reporter=dot
```

Browser smoke targets after implementation:

- `/zh`
- `/zh/instruments`
- `/zh/instruments/AAPL`
- `/zh/ai-research`
- `/zh/evidence`
- `/zh/watchlist`
- `/zh/portfolios`
- `/zh/reports`
- `/zh/alerts`
- `/zh/task-runs`
- `/zh/settings`

Viewport targets:

- 390x844
- 768x1024
- 1024x768
- 1440x900

## Risky Files And Rollback Points

- `apps/web/app/globals.css`: broad theme impact; validate both themes immediately after token edits.
- `apps/web/app/[locale]/layout.tsx`: shell scroll/fixed-nav changes can create hidden content or overflow.
- `apps/web/components/top-nav-bar.tsx`, `sidebar-navigation.tsx`, `mobile-navigation.tsx`: route reachability and active-state risk.
- `apps/web/components/financial-page-header.tsx`: shared page header changes affect migrated pages.
- `apps/web/components/ui/*`: primitive changes can cascade across the site.
- `apps/web/messages/en.json`, `apps/web/messages/zh.json`: keep keys synchronized.

Rollback by wave: if a later page migration introduces instability, revert that page/component group while keeping earlier token and shell work.

## Follow-Up Checks Before `task.py start`

- `prd.md`, `design.md`, and `implement.md` have been reviewed or explicitly approved.
- This task remains scoped to whole-site UI system work, not professional-terminal feature parity.
