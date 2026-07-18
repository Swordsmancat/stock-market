# Investment Calendar Contract

## Scenario: Database-first personal investment calendar

### 1. Scope / Trigger

Use this contract when changing the investment-calendar projection, its month/day UI, or the stored event sources it exposes. It prevents month views from silently truncating data, mixing time zones, fabricating company-event semantics, or calling providers during normal page reads.

### 2. Signatures

```text
GET /investment-calendar
  start: date
  end: date
  kind: economic | company = economic
  min_importance: integer 0..5 = 0
```

Implementation owners:

- Router: `apps/api/routers/investment_calendar.py`
- Service: `packages/services/investment_calendar.py`
- Page: `apps/web/app/[locale]/investment-calendar/page.tsx`
- Shared frontend decoder/query helpers: `apps/web/lib/investment-calendar.ts`

The endpoint reads `economic_calendar_events` for economic events. Company events read `official_disclosures` only when the disclosure symbol belongs to an active `watchlist_items` row with `market = CN`.

### 3. Contracts

Requests contain 1-42 inclusive Shanghai calendar days. `min_importance` applies only to economic source ratings; company disclosures remain unrated and must not be assigned a synthetic score.

The response contains:

```json
{
  "status": "ok",
  "start": "2026-07-01",
  "end": "2026-07-31",
  "kind": "economic",
  "count": 1133,
  "truncated": false,
  "days": [
    {
      "date": "2026-07-16",
      "count": 62,
      "max_importance": 3,
      "items": []
    }
  ]
}
```

Each item carries stable `id`, `kind`, Shanghai-local `date` and `time`, `title`, nullable `importance`, source identity/URL/retrieval time, and kind-specific optional evidence fields. Reads are capped at 2,500 items and set `truncated=true` when another row exists. The observed July 2026 month has 1,133 distinct events, so the cap preserves a complete real month while remaining bounded.

Frontend URL state uses `month=YYYY-MM`, `date=YYYY-MM-DD`, `kind=economic|company`, and `importance=0..5`. Invalid values fall back to the current Shanghai month, an in-range selected date, economic kind, and importance zero.

No environment key is required. Page GET requests use the normal `API_BASE_URL` backend connection and must not invoke provider refresh, ingestion, or write endpoints.

### 4. Validation & Error Matrix

| Condition | Result |
|---|---|
| `end < start` or range exceeds 42 days | HTTP 400 with bounded-range detail |
| Unknown `kind` | FastAPI HTTP 422 |
| `min_importance` outside 0..5 | FastAPI HTTP 422 |
| Valid range with no stored rows | HTTP 200, `count=0`, `days=[]` |
| More than 2,500 matching rows | HTTP 200, first 2,500 rows, `truncated=true` |
| Backend unavailable or payload fails frontend decoder | Localized failure state, distinct from empty |
| Company event lacks source importance | `importance=null`; no synthetic rating |

### 5. Good / Base / Bad Cases

- Good: July returns all 1,133 stored events, grouped by Shanghai date, with `truncated=false`.
- Base: A month with no active-watchlist disclosures renders a truthful company-event empty state.
- Bad: Reusing `/economic-calendar/events?limit=200` for month counts silently under-reports the month.
- Bad: Refreshing Eastmoney from the page request couples availability, latency, and writes to a read surface.
- Bad: Labeling every disclosure as three-star or five-star invents evidence not present in metadata.

### 6. Tests Required

- Service: assert more than 200 events survive one month, day grouping totals match, and adjacent UTC timestamps respect Shanghai boundaries.
- Service: assert only active CN watchlist disclosure symbols appear and their importance is null.
- Router: assert empty database response, 42-day range error, and unknown-kind validation.
- Frontend helpers: assert malformed query fallback, leap/month-end calculation, Monday-first 42-cell grid, and response decoding.
- Page/component: assert endpoint query construction, selected-day agenda switching without refetch, explicit failure versus empty state, and desktop-only navigation ownership.
- Runtime: assert complete real-month count, desktop/mobile no horizontal overflow, light/dark readability, and no console errors.

### 7. Wrong vs Correct

#### Wrong

```typescript
const response = await backendFetch(
  `/economic-calendar/events?start=${start}&end=${end}&limit=200`,
);
```

This treats a table endpoint's presentation cap as a complete month projection.

#### Correct

```typescript
const response = await backendFetch(
  `/investment-calendar?start=${start}&end=${end}&kind=${kind}&min_importance=${importance}`,
  { cache: "no-store" },
);
```

The dedicated contract returns grouped, bounded, database-only calendar evidence and exposes truncation explicitly.
