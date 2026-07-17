# Read-Only Database Storage Overview Contract

## 1. Scope / Trigger

Use this contract when exposing database inventory or disk-usage information to
the personal research UI. The feature reports what the existing application
database stores; it is not a database administration surface and does not add
models or migrations.

## 2. Signatures

- Service: `get_storage_overview(session: Session) -> dict[str, object]` in
  `packages/services/storage_overview.py`.
- API: `GET /storage/overview` in `apps/api/routers/storage.py`.
- Page: `/{locale}/storage` in
  `apps/web/app/[locale]/storage/page.tsx`.
- Navigation: desktop-only `/storage` item in
  `apps/web/components/navigation-items.ts`; the mobile bottom bar remains five
  items.

## 3. Contracts

The API is database-only and read-only. It returns:

```json
{
  "status": "ok",
  "engine": "PostgreSQL",
  "row_count_kind": "estimated",
  "collected_at": "ISO-8601 UTC timestamp",
  "summary": {
    "table_count": 34,
    "estimated_rows": 30000,
    "data_bytes": 333000000,
    "index_bytes": 141000000,
    "total_bytes": 474000000
  },
  "domains": []
}
```

Each domain repeats the five summary fields and contains `tables`. Each table
contains `name`, `estimated_rows`, `data_bytes`, `index_bytes`, and
`total_bytes`. Byte fields are nullable when the database does not expose safe
size metadata.

PostgreSQL reads `pg_class`, `pg_namespace`, and `pg_stat_user_tables` in the
current schema. Row counts use `n_live_tup`/`reltuples` and must be labeled
estimated. Normal page reads never issue production `COUNT(*)` scans. SQLite
compatibility may use exact counts because it is limited to isolated tests and
small development databases; its size fields remain `null`.

`DOMAIN_TABLES` is the single classification owner. Every unknown future table
falls into `other`; the UI must not silently hide it. Aggregates are computed
from the returned table rows in the service, not independently in the router or
page.

The payload never includes database URLs, hostnames, usernames, credentials,
environment values, SQL text, schema DDL, or stored row content.

## 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| PostgreSQL catalog read succeeds | Return estimated counts and byte sizes |
| SQLite test/development session | Return exact counts and nullable sizes |
| Unknown application table | Include it under `other` |
| Unsupported engine | Raise `StorageOverviewUnavailable`; HTTP 503 |
| SQLAlchemy catalog failure | Roll back session; sanitized HTTP 503 |
| API returns malformed payload | Page renders explicit `ErrorState` |
| Successful payload has no domains | Page renders explicit empty state |

## 5. Good / Base / Bad Cases

- Good: a large PostgreSQL database opens quickly using catalog estimates and
  shows table, data, index, and total sizes by research purpose.
- Base: an empty initialized database returns zero-estimate table rows and
  remains visibly different from an unavailable API.
- Bad: run `COUNT(*)` over every production table, expose the configured
  database URL, hard-code sample card values, or add truncate/vacuum/migration
  buttons to this page.

## 6. Tests Required

- Service tests cover aggregation, known and unknown table classification,
  SQLite exact counts, and nullable sizes.
- API tests cover successful delegation and sanitized 503 payloads without the
  original exception or connection text.
- Page tests cover summary cards, domain/table rendering, read-only behavior,
  malformed/failure distinction, and the named focusable table scroll region.
- Navigation tests assert the desktop link and unchanged five-item mobile bar.
- Browser acceptance checks desktop and `390x844` mobile widths, no page-level
  horizontal overflow, internal table scrolling, both themes, and no console
  errors.

## 7. Wrong vs Correct

### Wrong

```python
for table in tables:
    rows = session.execute(text(f"SELECT COUNT(*) FROM {table}"))
return {"database_url": settings.database_url, "rows": rows}
```

This scans large tables, interpolates identifiers, and leaks connection
configuration.

### Correct

```python
rows = session.execute(_POSTGRES_TABLE_STATS).mappings()
return _build_storage_payload(
    engine="PostgreSQL",
    row_count_kind="estimated",
    table_rows=[dict(row) for row in rows],
)
```

The SQL is static and read-only, estimates are explicit, and the projection is
secret-safe.
