# Investment calendar design

## Boundaries

The feature owns a read-only monthly projection over already persisted research evidence. Collection remains in existing refresh/background workflows. The normal page render never performs provider calls or database writes.

## Backend contract

Add `GET /investment-calendar` with `start`, `end`, `kind`, and `min_importance` parameters. The range must contain 1-42 days, which covers a displayed month plus calendar padding while preventing unbounded reads.

The response contains the normalized range, kind, total count, and day buckets. Every item has a stable id, kind, local date/time, title, importance, optional country/symbol/values/unit/source metadata, and retrieval timestamp.

Economic items query `EconomicCalendarEvent` directly with Shanghai-to-UTC boundaries and a safe 2,500-item cap. The payload reports truncation explicitly if the cap is reached. The bound covers the observed 1,133-row July 2026 month without returning an unbounded result.

Company items join active watchlist membership to stored official disclosures and use disclosure publication time as the calendar time. This keeps personal scope bounded and avoids implying knowledge the database does not contain.

## Frontend architecture

The localized route is a server component that parses bounded search parameters, fetches one API projection, and passes it to a client calendar component. The client owns selection and navigation through localized router query updates. Month/kind/importance changes cause a server refetch; selecting a date reuses the current payload.

Desktop uses a stable two-column grid: month calendar and selected-day agenda. Mobile stacks the agenda below the calendar. Day cells are buttons with selected/today states, fixed minimum height, count text, and an importance label/marker. The agenda uses an unframed list separated by rules.

## Compatibility and failure behavior

- Existing `/economic-calendar/events` remains unchanged for current consumers.
- No migration is needed; the feature reads existing tables.
- API failure renders a localized unavailable state while navigation and month controls remain usable.
- An empty month or empty selected day is distinct from API failure.
- Unknown or malformed URL values fall back to the current Shanghai month, economic kind, importance zero, and the first valid in-range date.

## Verification

Validate the service/router with unit and API tests, frontend utilities/components with the existing test stack, and the running app with desktop/mobile screenshots in light and dark themes. Confirm no page-level horizontal overflow and that `/`, API health, and existing 3000/8000 services remain available.
