# Improve core information display - Design

## Summary

This task turns the existing market-data display screens from raw panel collections into a clearer information product. The dashboard becomes the primary command center for data health and watchlist status. Instrument detail becomes a focused single-symbol daily story. Instruments and reports keep their current capabilities but gain scannable summaries and cleaner preview hierarchy.

## Product decisions

- Dashboard first: the dashboard is the primary information command center.
- Detail second: instrument detail should deepen the selected symbol story.
- Instruments and reports receive supporting scanability improvements.
- Dashboard primary subject is data health plus watchlist overview.
- A single primary instrument is a fallback focus item, not the dashboard's main identity.
- Portfolio panels remain secondary because current portfolio data is demo-oriented.
- Missing or stale data should show a primary ingestion/refresh action first, with diagnostics as secondary links.
- Dashboard may be strongly reorganized; lower-priority demo or secondary panels can move below the first screen.
- Daily movement uses text-first neutral semantics, not red/green-only market color conventions.
- Dashboard data-health scope is watchlist-first; if the watchlist is empty, use the first 25 instruments as a clearly labeled default sample.

## Current architecture

### Dashboard

- File: `apps/web/app/[locale]/page.tsx`
- Server component that fetches instruments, latest bar, bars, reports, portfolio, indicators, fundamentals, news, latest task run, watchlist, and alerts.
- Existing ingestion and analysis forms are already wired through Server Actions.
- Existing flash banners can include links.

### Instruments page

- File: `apps/web/app/[locale]/instruments/page.tsx`
- Server component that fetches instruments and latest daily bars for a bounded visible list.
- Already has freshness helpers and provider/source display.

### Instrument detail

- File: `apps/web/app/[locale]/instruments/[symbol]/page.tsx`
- Server component that fetches daily bars, reports, indicators, fundamentals, and news.
- Already has chart, daily bar summary, OHLCV table, source/provider, freshness, and task/report flash links.

### Reports page

- File: `apps/web/app/[locale]/reports/page.tsx`
- Server component that fetches paginated reports and renders markdown previews as raw substrings.

## Data flow

```text
Backend market-data/report endpoints
  -> backendFetch in server pages
  -> page-local payload types and derived display models
  -> localized summary cards/tables/empty states
```

No new backend contract is planned for this iteration. The UI should derive display state from existing payloads:

- latest daily bar payloads for source/provider/as-of/freshness
- recent bars for daily change and chart range
- watchlist payload for dashboard health scope
- task-run payload for last background work status
- report content for readable insight previews

## Dashboard design

### Data-health scope

Build a bounded dashboard health set:

1. If watchlist has entries, map watchlist symbols to instruments and latest daily bars.
2. Otherwise use the first 25 instruments as the default sample.
3. Label the scope explicitly as watchlist or default sample.

### Health buckets

Reuse the existing freshness semantics:

- `fresh`: latest daily bar is within the existing frontend freshness window.
- `stale`: latest daily bar exists but is outside the freshness window.
- `no_data`: endpoint reports no data or no latest item exists.
- `unavailable`: request failed or timestamp is invalid.

### First-screen layout

Recommended first-screen hierarchy:

1. Page title and concise description.
2. Primary command card:
   - data-health scope label
   - total checked instruments
   - fresh/stale/no-data/unavailable counts
   - active provider
   - latest task-run status
   - primary next action
   - secondary links to task runs, settings, and instruments
3. Watchlist/data-health panel:
   - watched or sample symbols needing attention
   - alert count when available
4. Primary instrument story panel:
   - latest close
   - daily absolute and percentage change when two bars exist
   - latest bar date
   - source/provider/freshness
   - mini chart
   - links to instrument detail and reports
5. Existing secondary panels below the fold.

## Instrument detail design

Derive daily movement from the last two daily bars:

- `change = latest.close - previous.close`
- `changePercent = previous.close === 0 ? null : change / previous.close`

Display direction with explicit sign, arrow, and localized label. Color can be subtle but must not be the only signal.

The first screen should include:

- latest close
- daily change and percentage change
- volume
- latest bar date
- freshness
- source/provider
- chart range
- primary ingestion/refresh action where available
- secondary task-run/settings links for diagnostics

## Instruments design

Add a summary layer above the table using the latest daily bar results already fetched for visible instruments:

- visible count
- fresh count
- stale count
- no-data count
- unavailable count
- active provider/source context

The table remains the detailed scan surface.

## Reports design

Replace arbitrary substring previews with a small parser that extracts a readable report title or first meaningful line:

1. Prefer the first markdown heading after removing leading `#` markers.
2. Otherwise use the first non-empty line.
3. Trim markdown emphasis/bullets enough for table readability.
4. Fall back to the existing localized empty preview text when content is blank.

This is display-only and does not alter report generation quality.

## Localization

All new user-facing strings must be added to both:

- `apps/web/messages/en.json`
- `apps/web/messages/zh.json`

Copy must describe daily bars honestly and must not imply true real-time quotes.

## Testing strategy

Update focused frontend tests for changed behavior:

- dashboard page summary, next action, and data-health scope label
- instruments page data-health summary
- instrument detail daily movement and first-screen data-health story
- reports page readable preview extraction

## Trade-offs

- Frontend-only aggregation avoids backend scope creep but keeps health checks bounded.
- Watchlist-first health is more user-relevant than whole-market health, but the empty-watchlist fallback must be labeled carefully.
- Strong dashboard reorganization may require broader test updates, but it directly addresses the product complaint that important information is not prominent.
