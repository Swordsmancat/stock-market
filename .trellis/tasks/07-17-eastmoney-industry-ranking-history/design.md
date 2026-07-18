# Technical design

## Boundaries

- A dedicated Eastmoney provider owns public endpoint requests and response
  normalization. Its transport is injectable for deterministic tests.
- Platform settings store optional proxy and Cookie secrets. Public settings
  expose only configured booleans.
- A service refreshes the industry universe and bounded daily histories,
  computes deterministic ranks, and upserts a complete revision transaction.
- A database-only query returns a bounded date-by-rank projection.
- The existing sectors router exposes explicit refresh and read endpoints.
- The Evidence Center renders a localized horizontally scrollable matrix and
  never starts a refresh merely because the page loads.

## Access policy

Each request uses the canonical public host first, then the public
`push2delay` host. Only after the bounded direct host sequence fails may the
same sequence run through the configured HTTP(S) proxy. Empty or rejected
schemas advance to the next host, and a provider-wide zero-row result fails
without modifying stored evidence. The optional Cookie is attached only when
supplied manually. Diagnostics use a small allowlist of codes and never contain
request URLs with credentials, headers, response bodies, or exception text.

## Storage

Add an industry daily ranking table keyed by provider, taxonomy, industry code,
and trade date. Store normalized name, change percent, computed rank, source
identifier, retrieval time and non-secret audit metadata. Refresh gathers and
validates data before the transaction so a provider-wide failure preserves the
last complete stored projection. Repeated refreshes revise matching rows.

## Data flow

Explicit UI refresh -> Web proxy -> FastAPI router -> refresh service ->
Eastmoney provider -> normalized rows -> PostgreSQL. Page load and GET follow
PostgreSQL -> service projection -> FastAPI -> Web proxy/component only.

## Rollout and rollback

The migration is additive. Empty storage is a truthful empty state. If live
access remains blocked without a working proxy, deployment remains usable and
reports a secret-safe access diagnostic; existing hot-sector behavior is
unchanged. Rollback removes the new panel/routes/service/provider and reverses
only the additive table migration.
