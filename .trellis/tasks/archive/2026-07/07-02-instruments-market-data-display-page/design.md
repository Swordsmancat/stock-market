# Instruments market-data display page - Design

## Summary

This child task adds a dedicated instruments page at `apps/web/app/[locale]/instruments/page.tsx`. The page gives users an obvious entry point for browsing instruments and checking whether latest daily-bar data exists, where it came from, and how fresh it is.

The page is intentionally daily-bar focused. It must not imply real-time quote semantics because the backend provider contract currently exposes historical bars, latest daily bars, and provider/source metadata only.

## Current state

Relevant files:

- `packages/services/instruments.py`
- `apps/api/routers/instruments.py`
- `apps/web/app/api/instruments/route.ts`
- `apps/web/app/[locale]/page.tsx`
- `apps/web/app/[locale]/instruments/[symbol]/page.tsx`
- `apps/web/components/sidebar-navigation.tsx`
- `apps/web/components/mobile-navigation.tsx`
- `apps/web/messages/en.json`
- `apps/web/messages/zh.json`

Current behavior:

- The backend already exposes `GET /instruments` with `source` and `items`.
- Each instrument item can include `symbol`, `name`, `market`, `exchange`, `asset_type`, `currency`, and item-level `source`.
- Existing pages link to instrument detail pages, but there is no list page at `/instruments`.
- The dashboard fetches only the first instrument and therefore does not solve browsing or market-data availability.
- `GET /market-data/{symbol}/latest` now returns latest daily-bar metadata, including no-data state when no bars are available.

## Target page behavior

The `/instruments` page should:

- Fetch instrument list data with `backendFetch("/instruments")`.
- Fetch platform settings to determine the effective provider used for latest daily-bar fallback.
- Fetch latest daily-bar payloads for a bounded number of visible instruments, using `withProviderQuery`.
- Render a table with:
  - symbol;
  - name;
  - market;
  - latest close;
  - latest timestamp/as-of;
  - source/provider;
  - freshness badge;
  - detail and follow-up links.
- Use `EmptyState` when the backend returns a successful empty instrument list.
- Use `ErrorState` when the instrument list request itself fails.
- Add desktop and mobile navigation entries.

## Data shape

Instrument list payload:

```ts
type InstrumentsPayload = {
  source: string;
  items: Instrument[];
};
```

Latest daily-bar payload:

```ts
type LatestDailyBarPayload = {
  symbol: string;
  source: string;
  provider?: string | null;
  requested_provider?: string | null;
  effective_provider?: string | null;
  status?: "ok" | "no_data" | string;
  no_data_reason?: string | null;
  item?: {
    timestamp?: string;
    close?: number;
  } | null;
};
```

If the latest-bar request fails for an individual symbol, the page should not fail the whole list. It should render that row with unavailable latest data and an actionable hint.

## Freshness semantics

Freshness is based on the latest daily bar timestamp:

- `fresh`: latest bar is less than or equal to three calendar days old.
- `stale`: latest bar is older than three calendar days.
- `no_data`: latest payload has no latest daily bar.
- `unavailable`: latest payload request failed or timestamp could not be parsed.

These are user-facing labels only. They do not replace backend quality diagnostics.

## Out of scope

- Real-time quote support.
- Full client-side search/filtering interactions.
- Schema changes to store provider lineage per `DailyBar`.
- Reworking the instrument detail page; that is handled by the next child task.
