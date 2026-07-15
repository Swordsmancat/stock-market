# Implementation plan

1. Add focused regressions for the global-search hydration boundary, keyboard
   open/close behavior, and market-preserving result navigation.
2. Convert the top bar to a server component and verify independent client
   islands in a clean browser session.
3. Extend the optional assistant snapshot contract through frontend types,
   API validation, service context/citations/diagnostics, and response context.
4. Wire daily shortlist and detail-page snapshot IDs into
   `MarketAssistantCard`; clear stale AI-desk context on ordinary selection.
5. Add exact instrument identity resolution plus a side-effect-free watchlist
   membership service/API query and a localized detail-page watch toggle.
6. Separate watchlist failed/empty states, add market-aware currency formatting,
   and remove synthetic detail zero values.
7. Run focused tests after each slice, then frontend lint/type/tests, relevant
   Python API/service tests, Trellis full checks, and browser acceptance at
   1280x720 and 375x812.
8. Confirm the diff excludes the protected homepage and all pre-existing user
   changes; update specs only for durable contracts, commit this task alone,
   archive it, then restore the five-day acceptance task as current.
