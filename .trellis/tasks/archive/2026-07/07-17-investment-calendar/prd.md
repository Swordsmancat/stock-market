# Add investment calendar

## Goal

Provide a practical, database-first investment calendar for personal research. The page should make a month of scheduled economic releases easy to scan and make the selected day's stored evidence easy to inspect without triggering collection during page load.

## Requirements

- Add localized `/investment-calendar` pages for Chinese and English.
- Add a desktop sidebar entry and breadcrumb label. Keep the mobile bottom navigation at five items.
- Present a month grid and a selected-day agenda inspired by the supplied reference image, using the existing terminal-style visual system rather than copying its branding.
- Support previous month, next month, today, selected date, event kind, and minimum-importance controls.
- Make calendar state URL-addressable with bounded query parameters.
- Use Shanghai calendar dates consistently for grouping and display.
- Read economic events from persisted `economic_calendar_events`; page GET requests must not call Eastmoney or any other external provider.
- Return the complete bounded month rather than truncating at the existing 200-row economic-calendar limit.
- Use stored official disclosures only for company events, bounded to active watchlist instruments. Do not fabricate earnings, dividend, IPO, or corporate-action dates.
- Display event time, country, name, importance text/shape, previous, forecast, actual, unit, source, and stored-data freshness when available.
- Provide truthful loading-independent empty, partial, and API-failure states.
- Preserve the existing homepage, market-research page, normal Docker services, and unrelated dirty files.
- Work in light/dark themes and remain usable without horizontal page overflow on desktop and mobile.

## Acceptance Criteria

- [x] A user can open `/zh/investment-calendar` and `/en/investment-calendar` from the desktop sidebar.
- [x] The selected month is rendered as a correct seven-column calendar with daily event counts and non-color-only importance markers.
- [x] Selecting a day updates the visible agenda and URL without an external data refresh.
- [x] Month, kind, and minimum-importance controls produce bounded database-only API queries.
- [x] A populated July 2026 month is not truncated at 200 economic events.
- [x] Company events are derived only from stored official disclosures for active watchlist instruments, with an explicit empty state when none exist.
- [x] API and service tests cover validation, Shanghai date boundaries, grouping, full-month result bounds, and disclosure scoping.
- [x] Frontend tests cover calendar query parsing, grouping/presentation, navigation entry, and localized copy.
- [x] Lint, type checking, relevant tests, Trellis Check, and responsive browser verification pass.
