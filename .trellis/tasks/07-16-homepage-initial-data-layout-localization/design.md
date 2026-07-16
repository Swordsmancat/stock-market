# Homepage initial data, layout, and localization design

## Boundaries

The change stays in the server-rendered homepage, its translation catalogs, and
colocated tests. The backend API, database, provider adapters, cache TTL, and
stored evidence contracts remain unchanged.

## Data Flow

```text
homepage server component
  -> GET /dashboard/market-overview (20s read budget)
  -> cached or cold read-only dashboard aggregation
  -> stored macro/index projection
  -> localized homepage rows
```

The longer budget is not a refresh action. It only lets the existing cold GET
complete. Other optional reads keep their current five-second isolation.

## Timeout Design

- Keep `OPTIONAL_DASHBOARD_FETCH_TIMEOUT_MS=5000` for latest bars, news,
  instruments, watchlist, and hot sectors.
- Add a named market-overview timeout constant set to 20000 and use it only in
  `fetchMarketOverviewResult`.
- Preserve abort cleanup and the current failed result on non-2xx, abort,
  transport, or parse failure.

## Localization Design

- Define one page-local code-to-Dashboard-message-key registry for all nine
  built-in favorites.
- Resolve a known code through `t(...)` in both locales. Unknown codes fall back
  to stored name, then code.
- Remove the raw code subtitle from macro rows in both locales. Codes remain in
  the payload and are used internally for matching and localization.
- Translation catalogs remain symmetric.

## Layout Design

- Change the six-panel grid from three columns to two columns at `xl`, yielding
  three natural rows while keeping the existing panel heights and module order.
- Do not stretch fixed-height charts or add viewport-locked nested scrolling.
- Below `xl`, the existing single-column flow remains authoritative.

## Compatibility And Rollback

- No payload or persistence migration is required.
- Rollback restores the market-overview timeout, three-column desktop grid, and
  raw backend names. Redis cache contents remain valid.
