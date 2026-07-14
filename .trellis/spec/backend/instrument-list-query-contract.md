# Instrument List Query Contract

## Scenario: Additive Bounded Instrument Listing

### 1. Scope / Trigger

- Trigger: a UI needs searchable or paged instrument rows without downloading
  the complete A-share universe or issuing market-data requests for every row.
- Scope: `packages/services/instruments.py`, `GET /instruments`, the same-origin
  Next proxy, the Instruments page, and Global Search.
- Non-goals: cursor pagination, changing instrument identity, deleting legacy
  complete-list behavior, or changing quote/bar provider contracts.

### 2. Signatures

- Service: `list_instruments_payload(session=None, query=None, market=None,
  limit=None, offset=0) -> dict[str, object]`.
- API: `GET /instruments?q=<optional>&market=<optional>&limit=<optional>&offset=0`.
- Query constraints: `limit` is omitted or `1..100`; `offset >= 0`.
- Response fields: `source`, `items`, `total`, `limit`, `offset`, `has_more`.

### 3. Contracts

- Omitting `limit` preserves the legacy complete filtered list. The response
  still adds metadata with `limit=null`, `offset=0`, and accurate `total`.
- Filtering by query and market happens before counting and pagination.
- Database-backed results filter, count, order, offset, and limit in SQL. The
  small deterministic seed fallback filters first and slices in memory.
- Database order is stable by market code then symbol. `total` describes the
  complete filtered result, not the returned page.
- `has_more` is `offset + len(items) < total`; an offset beyond the result set
  returns an empty page rather than changing `total`.
- The Next proxy forwards query parameters unchanged. It does not reimplement
  filtering or pagination.
- The Instruments page requests 25 rows from URL `page` state and limits quote,
  bar, and comparison fan-out to that page. Global Search waits for non-blank
  input and requests at most 10 matching rows.

### 4. Validation & Error Matrix

- `limit < 1` or `limit > 100` at HTTP boundary -> FastAPI HTTP 422.
- `offset < 0` at HTTP boundary -> FastAPI HTTP 422.
- Direct service call with invalid limit/offset -> `ValueError`.
- Blank query -> no text filter.
- Unknown market or unmatched query -> HTTP 200 with `items=[]`, `total=0`,
  and `has_more=false`.
- Database read/count failure -> rollback and use the bounded seed fallback.

### 5. Good/Base/Bad Cases

- Good: `limit=25&offset=25` returns the second stable page, reports the full
  filtered total, and enables the next link only when `has_more=true`.
- Base: a protected legacy caller omits `limit` and still receives every item.
- Base: search opens with a blank input and performs no instrument request.
- Bad: the browser downloads thousands of rows and slices them after rendering.
- Bad: the service paginates first and then applies market/query filters.
- Bad: latest-bar requests fan out across the complete universe.

### 6. Tests Required

- Service tests cover first/middle/beyond-end pages, query and market filters,
  seed fallback, invalid direct arguments, stable totals, and legacy omission.
- API tests cover HTTP bounds and additive response metadata.
- Next proxy tests assert arbitrary query forwarding and payload preservation.
- Instruments page tests assert URL page state, 25-row requests, previous/next
  links, retained filters, empty filtered results, and bounded fan-out.
- Global Search tests assert no request for blank input, debounced bounded query,
  at most 10 results, failure state, and no automatic retry.

### 7. Wrong vs Correct

#### Wrong

```typescript
const payload = await fetch("/api/instruments").then((response) => response.json());
const visible = payload.items.slice(0, 25);
```

This transfers the complete universe and encourages unbounded downstream work.

#### Correct

```typescript
const offset = (page - 1) * 25;
const payload = await fetch(`/api/instruments?limit=25&offset=${offset}`).then((response) => response.json());
```

The API owns filtering/counting/pagination and the UI works only with the
current bounded page.
