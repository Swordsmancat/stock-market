# Eastmoney Industry Ranking History Contract

- The provider owns the Eastmoney `push2` industry universe and `push2his`
  daily K-line schemas. Normalized records contain code, name, trade date,
  finite daily change percent, and retrieval time.
- Requests are direct-first. An optional configured HTTP(S) proxy receives at
  most one fallback attempt per failed request. A manually supplied Cookie may
  be attached; browser state is never harvested automatically.
- Proxy URLs and Cookies are secrets. Public settings expose only configured
  booleans, and diagnostics never include headers, credential URLs, upstream
  bodies, exception text, or stored secret values.
- Explicit refresh gathers and validates records before committing a complete
  revision. Provider failure preserves stored history. Rank order is change
  percent descending with industry code as the deterministic tie breaker.
- GET and page render are database-only and bounded to 20 dates by 20 ranks.
  Empty storage and failed loading are distinct localized states.
- The Evidence Center matrix is horizontally scrollable. It is research
  context only and must not initiate login, orders, or automated trading.

Implementation anchors:

- `packages/providers/eastmoney_industry_rankings.py`
- `packages/services/industry_rankings.py`
- `apps/api/routers/sectors.py`
- `apps/web/components/industry-ranking-history-panel.tsx`
- `docs/runbooks/eastmoney-industry-ranking-history.md`

## Scenario: Interactive stored ranking matrix

### 1. Scope / Trigger

- Trigger: the Evidence Center needs screenshot-style comparison and filtering
  without adding page-load provider requests or inventing momentum labels.

### 2. Signatures

- Database-only read: `GET /sectors/industry-rankings?days=20&limit=20`.
- Explicit write: `POST /sectors/industry-rankings/refresh?days={1..20}`.
- Client payload: `dates[]` plus `{date, rank, code, name, change_percent}[]`.

### 3. Contracts

- The server page requests the maximum bounded 20-by-20 projection once.
- View, ascending/descending order, top 10/20, and 5/10/12/20 day controls
  operate over that stored payload in the client component.
- `industry` and `level 1` selectors remain disabled until another stored
  taxonomy or level has a real provider contract.
- The top three visible rows use distinct rank badges. Positive, negative and
  zero values use movement text/color; color is never the only signal.
- Fire, rocket, leaf or persistence labels are not derived from change percent
  alone. Add them only after a stored, documented signal field exists.

### 4. Validation & Error Matrix

| Condition | Required behavior |
|---|---|
| No stored dates | Render controls plus a localized truthful empty state |
| GET failure | Render the page-level localized error state |
| Refresh failure | Preserve the matrix and show the localized failure message |
| More columns than viewport | Scroll inside the focusable matrix; no page overflow |
| Unknown/non-finite value | Render unavailable, never coerce it to zero |

### 5. Good / Base / Bad Cases

- Good: sort or view changes are immediate and issue no request.
- Base: empty storage still exposes the refresh and bounded filter controls.
- Bad: changing day count calls GET repeatedly, page load calls POST, or the UI
  adds a hot-sector emoji without stored provenance.

### 6. Tests Required

- Component tests assert ladder values, top badges, list switching, ascending
  order, bounded refresh URL, empty state and failure preservation.
- Page tests assert the server fetch is database-only and both locale catalogs
  resolve the complete label set.
- Browser smoke asserts controls are unique and operable and document width
  does not exceed viewport width at desktop size.

### 7. Wrong vs Correct

Wrong:

```tsx
useEffect(() => fetch("/sectors/industry-rankings/refresh"), []);
```

Correct:

```tsx
const visibleDates = payload.dates.slice(0, dayCount);
// POST only from the explicit refresh button; filters reuse stored payload.
```
