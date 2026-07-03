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
| K-line chart interactions | Mostly complete | Add missing MA60/YTD and make interaction behavior testable where practical. |
| Smart recommendations | MVP complete | Add detail links, stronger breakout/oversold tests, and explicit acceptance limits. |
| Hot sectors | Mock MVP | Add real/degraded data contract and avoid representing mock data as live sector flow. |
| Comparison analysis | Mostly complete | Add interaction coverage and enrich export output. |
| Intraday chart | Not complete | Add minute-chart contract, frontend display, and graceful fallback. |
| Market depth | Not complete | Add level-2 style contract and clear provider capability fallback. |
| Technical indicators | Partial | Complete MACD/KDJ integration and configurable display controls. |
| AI assistant | Partial report foundation | Add natural-language assistant entry point with traceable context and safe output boundaries. |

## Acceptance Criteria

- [ ] Each child task has a PRD with testable acceptance criteria.
- [ ] Complex child tasks have design and implementation plans before implementation starts.
- [ ] A Phase 2/3 remaining-work audit document records what is complete, partial, unavailable, or deferred.
- [ ] The completed implementation slices pass their targeted backend/frontend tests.
- [ ] The full web test suite passes before frontend slices are committed.
- [ ] Backend API/service slices pass relevant pytest tests before backend slices are committed.
- [ ] Every completed slice is committed and pushed to `origin/master` unless blocked by a failing quality gate.

## Notes

- This is a coordination task. Implementation should happen inside the child task whose acceptance criteria match the work being edited.
- The user has authorized automatic execution, testing, committing, and pushing for this Phase 2/3 completion effort.
