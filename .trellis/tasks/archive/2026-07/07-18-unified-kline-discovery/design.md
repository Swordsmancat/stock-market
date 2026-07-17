# Unified stored K-line discovery design

## Boundary

The feature is a read-only projection over `Instrument`, `Market`, `Exchange`,
and `DailyBar`. It owns no tables and invokes no provider registry. The
existing instrument detail route remains the full stock research destination;
the new workspace owns cross-asset discovery and stored daily K-lines.

## API

`GET /instrument-kline`

Query fields:

- `q`: optional trimmed text, maximum 64 characters.
- `asset_type`: optional `stock|etf|index`.
- `symbol`: optional exact symbol, maximum 64 characters.
- `market`: optional exact market code, maximum 16 characters.
- `period`: `1m|3m|6m|1y`, default `3m`.
- `limit`: catalog limit `1..50`, default `20`.
- `offset`: catalog offset `>=0`, default `0`.

Response fields:

- `status`: `empty|not_found|no_data|ready`.
- `source`: always `database`.
- normalized `query` projection.
- `catalog`: bounded active supported instruments with stored-bar summary.
- `total`, `limit`, `offset`, and `has_more`: filtered catalog pagination.
- `selected`: exact identity or null.
- `series`: coherent provenance, coverage, and finite OHLCV items or null.
- bounded diagnostic codes without secrets or upstream bodies.

The service queries storage directly. A database error returns an API failure;
it does not fall back to seed data or an external provider.

## Cohort Selection

For the exact selected instrument, group daily rows by normalized
`provider + adjustment`. Choose the cohort with the highest row count; break
ties lexically by provider then adjustment. Anchor the requested period to the
cohort's latest date and return only rows in that window, ordered ascending.
Rows with non-finite or invalid OHLC values are excluded; volume is nullable
only in the response normalization, never fabricated.

## Web

`/[locale]/instruments/kline` is a server page. URL state owns every choice.
The page performs one GET to the new API, renders type/search controls and a
bounded catalog, then passes selected rows to the existing client-side
`AdvancedCandlestickChart`. Links preserve filters where useful and exact
detail links include market identity.

The same-origin `/api/instrument-kline` proxy exposes the database-only catalog
to Global Search. Global Search reads the shared `catalog` projection and
preserves exact market identity for stock, ETF, and index results.

The existing Instruments page replaces per-row calls to
`/market-data/{symbol}/latest` with data returned by a database-only catalog
projection. This removes provider-capable fan-out from ordinary list reads.

## Failure And Rollback

- API unavailable: localized page-level error; no automatic retry.
- No stored instruments: explicit empty state.
- Exact selection missing: explicit not-found state; catalog remains usable.
- Selected identity has no coherent rows: explicit no-data state.
- Rollback removes the router, service, route, action link, translations, and
  tests; no migration or stored data changes are required.
