# Add stored Eastmoney economic calendar

## Goal

Persist and display a bounded public economic release calendar with explicit
refresh and database-only reads, optimized for a single-user research workflow.

## Requirements

- Add an `economic_calendar_events` PostgreSQL table with a stable Eastmoney
  occurrence identity, scheduled Shanghai time, country, indicator name,
  importance, period, previous/forecast/actual value, unit, and audit metadata.
- Use the public, Cookie-free Eastmoney
  `RPT_INFO_SCHEDULENEWSNEW` report. Do not copy private mirrors or credentials.
- The provider must page through a caller-bounded date range, validate response
  shape, sanitize diagnostics, and never turn missing values into zero.
- Expose an explicit POST refresh for at most 62 calendar days and a GET query
  for at most 200 stored rows. GET must never fetch upstream data.
- Default display scope is the stored current-month calendar, ordered by
  scheduled time, with local filters for importance and country.
- Add a compact localized calendar panel to the Evidence Center below the macro
  dashboard; it shows time, country, importance, name, previous/forecast/actual,
  unit, and truthful empty/error states.
- Keep refresh manual and inside the panel; no Beat schedule, crawler, trading
  action, model request, or automatic page-load mutation.

## Acceptance Criteria

- [x] Provider normalization handles pagination, null numeric fields, exact
  Shanghai timestamps, and stable per-release identity.
- [x] Repeating an overlapping refresh is idempotent and updates revised actuals.
- [x] A failed provider call preserves all previously stored events.
- [x] GET date/importance/country/limit bounds are validated and database-only.
- [x] Chinese and English panels render loaded, empty, and refresh-failure states.
- [x] Migration upgrades/downgrades cleanly and focused/full checks pass.
- [x] Live explicit refresh stores real events and 3000/8000 stay healthy.

## Notes

- Keep `prd.md` focused on requirements, constraints, and acceptance criteria.
- Lightweight tasks can remain PRD-only.
- For complex tasks, add `design.md` for technical design and `implement.md` for execution planning before `task.py start`.
