# Rebalance instrument detail research layout

## Goal

Bring charts and research evidence into balanced independent desktop columns while preserving a scan-first mobile order.

## Requirements

- Preserve the page header, source-switch notice, and live AI assistant as the first detail-page workflow.
- Replace the stretched report/evidence grid with two independent desktop content streams at the existing `xl` breakpoint.
- Put K-line, intraday, latest news, and the saved AI report in the wider primary-review stream; put technical indicators and fundamentals in the narrower evidence stream.
- Use the same semantic DOM order on narrow screens so the page becomes one coherent sequence without CSS-only visual reordering.
- Keep every existing payload, empty/error/recovery state, action, chart, citation, and localized label unchanged.
- Do not modify the homepage, backend APIs, providers, or the active five-day acceptance task.

## Acceptance Criteria

- [x] The desktop detail layout has two independent top-aligned columns and no card is stretched to match the full height of the other column.
- [x] K-line appears before intraday, news, and the saved AI report in the wide column; technical indicators appear before fundamentals in the evidence column.
- [x] At 390px the layout is one column in DOM order: K-line, intraday, news, saved AI report, technical indicators, fundamentals.
- [x] The live AI assistant remains above the research grid and behaves exactly as before.
- [x] Existing news recovery, chart empty states, fundamentals disclosure, report links, and advanced market-data disclosure remain functional.
- [x] Desktop and mobile have no page-level horizontal overflow.
- [x] Focused component tests, full Web tests, TypeScript, and browser layout checks pass.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
- Browser QA: at 1280x720 the primary/evidence streams measured 1294px/1577px with a 283px difference and total detail scroll height of 2480px, down from the previous 5860px. At 390x844 the grid resolved to one 359px column in the required DOM order with no root or main horizontal overflow.
