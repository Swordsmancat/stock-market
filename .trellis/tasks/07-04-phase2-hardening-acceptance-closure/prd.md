# Phase 2 Hardening Acceptance Closure

## Goal

Close the remaining Phase 2 gaps for K-line, recommendations, hot sectors, and comparison analysis.

## Requirements

- Close the remaining Phase 2 acceptance gaps without regressing the existing dashboard.
- K-line chart must expose MA5, MA10, MA20, MA60 and include a YTD quick range while preserving dark-mode support.
- Smart recommendations must be actionable from the dashboard and link to the relevant instrument detail page.
- Recommendation API tests must directly cover breakout and oversold/rebound recommendation categories.
- Hot sector data must include an explicit status/source contract so demo or unavailable data is not presented as confirmed live market flow.
- Comparison analysis export must include enough summary and correlation data to be useful outside the UI.
- Frontend user-visible text added by this task must be localized in English and Chinese.

## Acceptance Criteria

- [ ] K-line chart shows MA60 and includes a YTD range option.
- [ ] Dashboard recommendation cards link to instrument detail pages.
- [ ] Backend recommendation tests cover breakout and oversold/rebound categories.
- [ ] Hot sectors payload/UI distinguishes `ok`, `degraded`, and `unavailable` or demo/mock status.
- [ ] Comparison report export includes correlation values and selected instrument summaries.
- [ ] Focused frontend/backend tests for the changed Phase 2 areas pass.
- [ ] `npm run test:web` passes after frontend changes.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
