# Stock and overlay comparison design

## Boundary

This child adds one database read service, one thin FastAPI router, and one
server-rendered comparison page. It reuses the existing client-side chart and
calculation modules. It removes automatic comparison-bar loading from the
general Instruments page and adds no table, migration, worker task, provider,
or write endpoint.

## Backend contract

`get_market_comparison_payload(*, session, market="CN", symbols=(), period="3m", query=None, search_limit=8)` returns:

- request identity: `status`, `market`, `symbols`, `period`;
- stored search results excluding already selected symbols;
- latest anchor date, requested period start, shared dates/count, and bounded
  diagnostics/missing symbols;
- selected items in request order with exact instrument identity, coherent
  provider/adjustment/source provenance, coverage dates, and finite daily bars;
- `data_mode="stored"`, `research_signal_only=true`, and explicit no-trading
  safety metadata.

The router accepts comma-separated `symbols`, `period=1m|3m|6m|1y`, optional
`q` of at most 64 characters, and `search_limit=1..12`. The service validates
again so non-HTTP callers preserve the same contract.

## Stored-series selection

1. Normalize symbols to uppercase, preserve first-seen order, reject more than
   four, and resolve exact active CN stock identities.
2. Search `Instrument`/`Market` directly when `q` is present; never call the
   seed-backed instrument service.
3. Resolve the maximum stored date across selected instruments and subtract the
   period's bounded calendar span.
4. Load bounded daily bars for selected IDs in one query.
5. Per instrument, group by `provider + adjustment`, choose the largest series
   with lexical tie-break, and discard rows outside that cohort.
6. Keep only finite close values with positive first/shared baselines; optional
   volume/amount are not required by the comparison response.
7. Intersect dates across valid selected series. The frontend receives only
   bars on exact shared dates so normalization, returns, and correlation all
   use one auditable observation window.

The payload is `ok` only with at least two valid instruments and at least two
shared dates. Missing requested symbols remain visible diagnostics and are not
replaced with search results or seed data.

## Frontend workflow

`/[locale]/instruments/compare` uses URL state:

- `symbols=000001,600519`
- `period=1m|3m|6m|1y`
- `q=<stored instrument search>`

The server page performs one comparison GET. Search results are add links;
selected stocks are compact removable rows with exact detail links and
provenance. Periods are segmented links. This keeps selection shareable,
refresh-safe, and functional without client-side search state.

`ComparisonTool` remains the chart/metric owner. A shared-date alignment helper
in `comparison-utils` trims all series before normalization. With two to four
valid items the page renders the existing overlay, interval summaries,
correlation matrix, and export. Empty, insufficient, no-data, and transport
failure states remain distinct.

## Compatibility and rollback

The API and route are additive. The Instruments list loses only its automatic
comparison data fetch/card and gains an action link. Existing detail, search,
K-line, and report routes remain unchanged. Rollback restores the old embedded
card and removes the new router/page without touching stored data.
