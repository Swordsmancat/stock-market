# Design

## Architecture and boundaries

```text
AkShare public frames
  -> AkShare macro normalizer (schema/date/value validation)
  -> MarketIndicatorObservationSeed rows
  -> existing validated upsert/storage service
  -> read-only grouped dashboard projection
  -> FastAPI routes
  -> Next.js server page + client refresh action
```

The provider boundary owns volatile Chinese column names and source ordering.
The market-indicator service continues to own definitions, audited persistence,
and cache invalidation. The frontend consumes one typed projection and does not
interpret provider frames or database records.

## Provider adapter

Create a dedicated AkShare macro provider module with injectable family
fetchers. A declarative target table maps each family to:

- provider function and underlying public source URL;
- one date/period column parser;
- one or more stable indicator codes and value columns;
- unit, methodology, and bounded history size.

Normalize dates to period-end dates for monthly/quarterly data and exact dates
for daily series. Drop null/non-finite rows before storage. Sort by normalized
date so source order does not matter. A family error becomes a sanitized
diagnostic and does not abort successful families.

## Storage and retrieval

Extend the existing definition tuple and macro code list. Reuse the existing
unique `(indicator_id, as_of)` constraint and validated upsert path. Refresh
stores at most 24 recent valid observations per series. The read projection
queries each active indicator with a bounded history, computes comparable
latest/previous change, and returns chronological points.

No provider access occurs on GET. The explicit POST refresh stores results and
clears the market-overview cache only when observations were written.

## API contracts

- `GET /market-indicators/dashboard?history_limit=12`
  - grouped stored observations, counts, latest refresh date, no mutation;
  - `history_limit` is bounded.
- `POST /market-indicators/official-refresh/akshare-cn`
  - input: `family=all`, `history_limit=24`, `dry_run=false`;
  - output: fetched/stored/skipped counts, codes, latest date, per-family
    status, sanitized diagnostics, cache result.

## Frontend composition

Add a focused dashboard component at the top of `/evidence`. Use responsive
CSS grid cards and a small inline SVG sparkline with an accessible text summary.
The server loads the dashboard payload. A client refresh button calls a local
Next.js proxy route, reports progress/result, and refreshes the page.

All existing Evidence Center sections move as one unit into a closed native
`details` disclosure after the macro dashboard. This preserves power-user
operations without letting them dominate the personal-use view.

## Compatibility and rollback

- Existing nine codes and observation semantics are unchanged.
- Dashboard market-overview payload stays additive because its current macro
  item shape remains unchanged.
- Removing the new component/routes/definitions restores prior behavior;
  additional observation rows are harmless and auditable.

## Operational constraints

- External probes are sequential per refresh to avoid bursty provider traffic.
- Partial failure is expected and visible; stored history remains available.
- Deployment refresh is explicit and run once after tests, never on GET.
