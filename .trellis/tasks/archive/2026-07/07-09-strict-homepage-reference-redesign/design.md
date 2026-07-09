# Strict homepage reference redesign design

## Architecture And Boundaries

This is a frontend-only homepage presentation change in `apps/web`.

Primary target:

- `apps/web/app/[locale]/page.tsx`

Likely supporting targets:

- `apps/web/app/[locale]/page.test.tsx`
- `apps/web/messages/en.json`
- `apps/web/messages/zh.json`

The existing app shell, dark default, navigation, backend fetch helpers, market settings store, and provider capability contracts remain unchanged.

## Data Flow

The page continues to fetch:

- `getPlatformSettings()` for market provider, color scheme, homepage index preferences, macro preferences, and `news_search_provider_capabilities`.
- `/dashboard/market-overview` for indices, followed market bars, macro indicators, diagnostics, and generated timestamp.
- `/sectors/hot?limit=5` for sector ranking and flow values.
- `/news/{primaryInstrument.symbol}` for stored local news sentiment rows.
- Existing optional health/status endpoints for compact operational signals.

Derived frontend projections:

- `tickerItems`: same `buildHomeIndexItems(...)` output, preserving configured order.
- `macroRows`: same `favoriteMacroIndicatorRows`, rendered as compact table rows.
- `sectorRows`: hot-sector payload, rendered in table-like homepage panel rather than using the larger reusable `HotSectors` card if that component remains too spacious.
- `newsRows`: first 5 local news items.
- `marketOverviewSeries`: selected index/followed bars projected to compact SVG line paths.
- `fundFlowRows`: hot-sector net flow/fund flow values projected to compact SVG bars.
- `aiSentiment`: deterministic dashboard sentiment score from local signals such as news sentiment/confidence, data health counts, hot-sector direction, and provider readiness. The UI must label this as market sentiment/status, not investment advice.

## UI Structure

Desktop layout should use a dense dashboard grid:

- Top market band:
  - Left segmented controls.
  - Center market title.
  - Right add/settings action.
  - Two ticker groups using index favorites.
- Main grid:
  - 3 columns at wide desktop.
  - Two rows of panels with comparable heights.
  - Provider strip full-width at bottom.
- Mobile/tablet:
  - Stack panels in logical scan order.
  - Preserve table/list density without horizontal page overflow.

Panel styling:

- Dark card surfaces with thin borders.
- Small titles, compact descriptions only where useful.
- Table rows over large cards.
- Tabular figures.
- Blue active states.
- Existing market color scheme for red/green movement direction.
- Small SVG charts/gauge with fixed viewBox and stable dimensions.

## Compatibility Notes

- Keep homepage curated. Do not reintroduce AI research brief, recommendations, reports, K-line, technical indicators, or fundamentals into the homepage.
- Do not change backend payload types or API response shapes.
- Avoid exposing API keys or provider credentials. Provider status only uses capability metadata already exposed by the platform settings store.
- Keep translations in `apps/web/messages/en.json` and `apps/web/messages/zh.json`.

## Trade-Offs

- A homepage-local set of helper components is acceptable because the reference-specific layout is a one-off terminal cockpit. Extract only helpers that reduce real duplication.
- Exact screenshot pixel parity is not required, but the resulting geometry should clearly match the screenshot's structure and density.
- The AI sentiment gauge is a dashboard-derived status visualization until the backend exposes a dedicated sentiment metric.

## Rollback Shape

This change can be rolled back by reverting the homepage/test/message edits. Backend state and stored settings are unaffected.
