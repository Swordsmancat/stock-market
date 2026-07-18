# Eastmoney Industry Ranking History Contract

- The provider owns the Eastmoney `push2` industry universe and `push2his`
  daily K-line schemas. Normalized records contain code, name, trade date,
  finite daily change percent, and retrieval time.
- The canonical public source is Eastmoney Quote Center level-one industries:
  `https://quote.eastmoney.com/center/gridlist.html#industry_board_1`. The
  universe filter is `m:90 s:4`; `industry_board_2` and
  `industry_board_3` are different taxonomic levels and must not be mixed.
- Requests try the canonical public host directly, then the public
  `push2delay` host directly. An optional configured HTTP(S) proxy receives one
  bounded pass over the same hosts only after direct access fails. A manually
  supplied Cookie may be attached; browser state is never harvested
  automatically.
- A transport-level HTTP 200 is insufficient: an empty or schema-rejected
  universe/history response advances to the next permitted host. Individual
  industries may have no history, but a provider-wide zero-row result fails
  the refresh and preserves the stored projection instead of recording a
  successful no-op.
- When the provider returns only a usable subset, each touched trading date is
  re-ranked across its complete stored industry cohort in the same transaction.
  Incremental accumulation must never leave duplicate or stale daily ranks.
- Proxy URLs and Cookies are secrets. Public settings expose only configured
  booleans, and diagnostics never include headers, credential URLs, upstream
  bodies, exception text, or stored secret values.
- Explicit refresh gathers and validates records before committing a complete
  revision. Provider failure preserves stored history. Rank order is change
  percent descending with industry code as the deterministic tie breaker.
- GET and page render are database-only and bounded to 20 dates by 20 ranks.
  Empty storage and failed loading are distinct localized states.
- The read payload identifies `eastmoney_industry_level_1`, links the canonical
  source page, and serializes the latest retrieval time with an explicit UTC
  offset. A fallback provider is compatible only when it returns the exact
  Eastmoney level-one industry codes and names; incompatible taxonomies must
  remain separate rather than being merged into this ranking history.
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
- Client payload: `provider`, `taxonomy`, `source_url`, nullable
  `retrieved_at`, `dates[]`, plus
  `{date, rank, code, name, change_percent}[]`.

### 3. Contracts

- The server page requests the maximum bounded 20-by-20 projection once.
- View, ascending/descending order, top 10/20, and 5/10/12/20 day controls
  operate over that stored payload in the client component.
- `industry` and `level 1` selectors remain disabled until another stored
  taxonomy or level has a real provider contract.
- `taxonomy` is `eastmoney_industry_level_1`; `source_url` is the canonical
  Quote Center page, and `retrieved_at` is the latest stored row retrieval
  time serialized with a UTC offset. The client formats it in Shanghai time
  with the route locale and omits an invalid timestamp without hiding the
  source link.
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
| Missing or invalid retrieval time | Keep the canonical source link; omit the stored-time suffix |
| Fallback uses another industry taxonomy | Reject/separate it; never merge it into Eastmoney level-one history |

### 5. Good / Base / Bad Cases

- Good: sort or view changes are immediate and issue no request.
- Base: empty storage still exposes the refresh and bounded filter controls.
- Bad: changing day count calls GET repeatedly, page load calls POST, or the UI
  adds a hot-sector emoji without stored provenance.

### 6. Tests Required

- Component tests assert ladder values, top badges, list switching, ascending
  order, bounded refresh URL, source provenance, timestamp safety, empty state
  and failure preservation.
- Service/API tests assert canonical taxonomy/source fields, explicit UTC
  serialization, and a database-only GET path.
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
