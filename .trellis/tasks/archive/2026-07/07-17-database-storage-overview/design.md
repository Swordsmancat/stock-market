# Database Storage Overview Design

## Boundaries

The feature is a read-only projection over the existing database. It adds no
models or migrations.

```text
PostgreSQL catalogs / SQLAlchemy inspection
  -> storage inventory service
  -> GET /storage/overview
  -> Next.js server page
  -> localized summary, domain cards, table inventory
```

The service owns table-to-domain classification and aggregation. The router
only injects the existing SQLAlchemy session. The frontend consumes the typed
projection and owns only formatting and localization.

## Backend Contract

The payload contains:

- `status`, `engine`, `row_count_kind`, `collected_at`
- `summary`: table count, estimated rows, data/index/total bytes
- `domains`: code, table count, estimated rows, size totals, and table rows
- table rows: physical table name, estimated rows, data/index/total bytes

PostgreSQL reads `pg_class`, `pg_namespace`, and `pg_stat_user_tables` for the
current schema. `n_live_tup`/`reltuples` are estimates; relation-size functions
provide byte counts. SQLite compatibility uses SQLAlchemy inspection and exact
counts only in isolated tests/small local databases, with unavailable size
values represented as `null`.

Only application table statistics are returned. The response never contains a
database URL, schema SQL, connection identity, environment values, or row data.

## Domain Classification

A single backend mapping assigns every known table. Unknown tables fall into
`other`; this prevents new migrations from disappearing from the inventory.
Domain order is stable and product-facing. Aggregates are derived from table
rows after classification so totals cannot drift across layers.

## Frontend

`/storage` is a dense operational dashboard consistent with existing terminal
pages:

- `FinancialPageHeader` for engine and database totals
- a responsive card grid for scan-first domain totals
- an unframed, horizontally scrollable table inventory below the cards
- tabular figures, localized units, explicit estimate wording

Cards use existing semantic colors and Lucide icons. The page does not add a
marketing hero, gradients, nested cards, or action controls. The new navigation
entry is desktop-only to preserve the five-item mobile contract.

## Failure And Compatibility

- API/catalog failure returns HTTP 503 with a generic safe message.
- Page fetch failure renders `ErrorState`; an empty successful payload renders
  an empty state.
- No fallback invents counts or sizes.
- PostgreSQL remains the production source; SQLite exists only for compatible
  tests and lightweight development.

## Rollback

Remove the storage router/service, page/tests/translations, and navigation item.
No database rollback is required because there is no migration or mutation.
