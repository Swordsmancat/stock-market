# Instrument detail source freshness table - Design

## Summary

This child task strengthens `apps/web/app/[locale]/instruments/[symbol]/page.tsx` so the instrument detail page becomes a trustworthy single-symbol daily-bar workstation. The page should make it obvious whether daily bars loaded, where they came from, which provider was used, how fresh the latest daily bar is, and what raw OHLCV rows back the chart.

This work remains daily-bar focused. It must not imply real-time quote support because the backend does not yet expose a quote provider contract.

## Current state

Relevant files:

- `apps/web/app/[locale]/instruments/[symbol]/page.tsx`
- `apps/web/app/[locale]/instruments/[symbol]/page.test.tsx`
- `apps/web/components/price-chart.tsx`
- `apps/web/messages/en.json`
- `apps/web/messages/zh.json`

Current behavior:

- The detail page fetches `/market-data/{symbol}/bars` and passes the items into `PriceChart`.
- The page displays the latest close but does not prominently show daily-bar source, provider, freshness, count, or charted data range.
- The page does not expose recent raw OHLCV rows.
- A failed bars request is indistinguishable from a successful empty bars response because `fetchOptionalJson()` returns a fallback for both.
- `PriceChart` has English chart-control and empty-state labels embedded in the component.

## Target behavior

The detail page should:

- Load daily bars through a bars-specific result type that can distinguish loaded and failed states.
- Display a daily-bar summary card with:
  - latest close;
  - latest daily-bar as-of date;
  - source;
  - provider/effective provider;
  - freshness;
  - bar count;
  - charted date range.
- Keep the existing chart, report, indicator, fundamental, and news sections intact.
- Render an `ErrorState` when the bars request fails.
- Render an `EmptyState` when the bars request succeeds but no bars are available.
- Add a recent OHLCV table showing the latest daily bars backing the chart.
- Localize user-visible chart labels and all new page strings.

## Freshness semantics

Freshness is based on the latest daily bar timestamp:

- `fresh`: latest bar is less than or equal to three calendar days old.
- `stale`: latest bar is older than three calendar days.
- `no_data`: no daily bars were returned.
- `unavailable`: bars failed to load or the latest timestamp cannot be parsed.

These labels are presentation hints and do not replace backend quality diagnostics.

## Out of scope

- Real-time quote support.
- Schema changes for per-row provider lineage.
- Redesigning reports, fundamentals, news, watchlist, or task-run workflows.
- Network calls to real providers in tests.
