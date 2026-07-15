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
9. Add failing provider-symbol, market forwarding, and CN fallback tests before
   changing runtime behavior.
10. Extend daily-bar payloads with optional market-aware database filtering and
    resilient CN source selection using the existing coordinator; preserve
    single-provider behavior elsewhere.
11. Forward market through market-data and assistant APIs, detail loading, and
    `MarketAssistantCard`; prefer the bars effective provider over depth.
12. Add localized detail provenance for automatic source switches without
    rendering raw source-attempt errors.
13. Run focused provider/service/API/assistant/frontend tests, then full Python
    and frontend suites, ruff, TypeScript, translations, and production build.
14. Live-smoke a CN symbol through search, detail, and AI; verify effective
    provider/citations and that no normal `3000`/`8000` service is disrupted.

## Verification

- Full backend suite: `916 passed`.
- Full frontend suite: `91 files, 316 passed`; TypeScript and scoped Ruff pass.
- Translation JSON and `git diff --check` pass.
- Isolated live path `920000/CN`: yfinance returned no data, AkShare hist
  failed with a sanitized `ConnectionError`, and AkShare daily selected 11
  rows. Detail loaded 118 bars and AI cited `provider=akshare`.
- Desktop `1280x720` and mobile `375x812` checks found no document, body, or
  control horizontal overflow.
- Normal Web/API remained healthy on ports `3000/8000` with their original
  process IDs after the isolated stack was stopped.
