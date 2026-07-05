# Phase 2 and 3 Financial Features Completion

## Goal

Coordinate the remaining Phase 2 hardening and Phase 3 advanced financial terminal features.

## Requirements

- Use `07-03-financial-dashboard-enhance` as the source requirement set for Phase 2 and Phase 3 financial terminal features.
- Preserve the existing working Phase 1 and dashboard behavior while closing the remaining Phase 2 acceptance gaps.
- Track the remaining work as independently verifiable child tasks:
  - Phase 2 Hardening Acceptance Closure.
  - Technical Indicators Workbench.
  - Intraday Chart.
  - Market Depth Data.
  - AI Market Assistant.
  - Performance Data Fix as the shared reliability and data-readiness prerequisite.
- Keep every user-visible frontend label localized in English and Chinese.
- Prefer real backend data when available; when a provider cannot support a feature, expose explicit `unavailable` or `degraded` states instead of silently showing mock data as real data.
- Use focused tests for each child task before marking it complete.
- Automatically run validation, commit, and push completed slices when they pass quality checks.

## Completion Matrix

| Area | Current audit status | Required closure |
|---|---|---|
| K-line chart interactions | Complete for MVP | Professional workspace features remain: saved layouts, drawing tools, multi-chart grids, chart-linked alerts, and multi-timeframe sync. |
| Smart recommendations | Complete as research-signal MVP | Add backtesting, hit-rate/drawdown metrics, benchmark comparison, and stronger signal history before professional-grade claims. |
| Hot sectors | Provider-backed MVP | Verify production sector/fund-flow providers, breadth metrics, constituent contribution, and taxonomy governance. |
| Comparison analysis | Complete for MVP | Add deeper risk metrics, export refinements, and portfolio/watchlist-level comparison workflows. |
| Intraday chart | Provider-backed MVP | Achieve successful live smoke, add cache/storage, market-calendar/session windows, provider broadening, and streaming refresh. |
| Market depth | Provider-boundary MVP | Achieve reachable live provider smoke, schema-backed parser adaptation, entitlement governance, recent-trade/fund-flow production validation, and order-flow analytics. |
| Technical indicators | Complete for MVP | Add professional chart-workbench UX: parameter persistence, presets, custom formulas, and multi-pane layout management. |
| AI assistant | MVP available | Add multi-turn memory, report/news/filing retrieval, richer citations, freshness diagnostics, and watchlist-level research monitoring. |

## Acceptance Criteria

- [x] Each child task has a PRD with testable acceptance criteria.
- [x] Complex child tasks have design and implementation plans before implementation starts.
- [x] A Phase 2/3 remaining-work audit document records what is complete, partial, unavailable, or deferred.
- [x] The completed implementation slices pass their targeted backend/frontend tests.
- [x] The full web test suite passes before frontend slices are committed.
- [x] Backend API/service slices pass relevant pytest tests before backend slices are committed.
- [x] Every completed slice is committed locally or queued in the current Trellis archive cleanup; push remains a repository-operator action when the worktree is ready.

## Completion Notes (2026-07-05)

- All 14 tracked child tasks are completed or archived.
- Full backend validation passed: `python -m pytest -q` -> `287 passed`.
- Full frontend validation passed: `npm run test:web` -> `101 passed`.
- The implemented product meets MVP expectations for dashboard navigation, instrument detail, historical and intraday charts, indicators, hot sectors, recommendations, comparison, degraded-safe market depth, AI assistance, and documentation.
- Professional terminal parity remains intentionally out of scope for this parent completion and is tracked as follow-up provider/research/workspace tasks.

## Notes

- This is a coordination task. Implementation should happen inside the child task whose acceptance criteria match the work being edited.
- The user has authorized automatic execution, testing, committing, and pushing for this Phase 2/3 completion effort.
