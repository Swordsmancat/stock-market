# Stored Stock Comparison Contract

## Scenario: Read-Only A-Share Overlay Comparison

### 1. Scope / Trigger

- Trigger: a personal user selects two to four A-share stocks for normalized
  price, return, volatility, and correlation comparison.
- Scope: `packages/services/market_comparison.py`,
  `apps/api/routers/market_comparison.py`,
  `/[locale]/instruments/compare`, shared comparison utilities, localization,
  and focused service/API/page tests.
- Non-goals: provider refresh, ingestion, fixture fallback, ETFs, indexes,
  intraday data, AI conclusions, recommendations, portfolio actions, or
  trading.

### 2. Signatures

- Service:
  `get_market_comparison_payload(*, session, market="CN", symbols=(), period="3m", query=None, search_limit=8) -> dict[str, object]`.
- API:
  `GET /market-comparison?market=CN&symbols=000001,600519&period=1m|3m|6m|1y&q=<query>&search_limit=1..12`.
- Page: `GET /[locale]/instruments/compare` with `symbols`, `period`, and `q`
  as shareable URL state.

### 3. Contracts

- The service reads active CN stock identities and `DailyBar` rows directly
  from the injected session. API and page reads must not call a provider,
  crawler, ingestion, backfill, shortlist, AI, order, or fixture/seed fallback.
- Normalize symbols to uppercase, preserve first-seen order, deduplicate them,
  and accept at most four. Missing requested symbols remain explicit and are
  never replaced by a search result.
- Search is bounded to stored active CN stocks, excludes selected symbols, and
  returns exact instrument identity for add links.
- Anchor the period to the latest stored selected-stock date. For each stock,
  choose one coherent `provider + adjustment` cohort by largest bounded row
  count with lexical tie-breaks. Never splice cohorts within one series.
- Keep finite positive closes only. Intersect dates across every comparable
  selected series, then return only exact shared-date bars. All frontend paths,
  summaries, volatility, and correlations use the first exact shared date as
  their common baseline.
- Expose `empty_selection`, `insufficient_selection`, `no_data`, and `ok`
  states plus anchor/period dates, shared-date count, missing symbols,
  provenance, bounded diagnostics, `data_mode="stored"`, and research/no-
  trading safety metadata.
- The Instruments page owns the route link but performs no comparison-bar
  requests. The dedicated page uses URL add/remove/period links and keeps the
  five-item mobile navigation unchanged.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Market other than CN, unknown period, query over 64, or invalid limit | HTTP 422; no comparison work |
| More than four normalized symbols | HTTP 422; no silent truncation |
| No symbols | `empty_selection`; stored search may still return results |
| One symbol | `insufficient_selection`; preserve identity/provenance |
| Requested symbol is missing/inactive/non-stock | Preserve it in `missing_symbols`; never substitute |
| Fewer than two comparable series or exact shared dates | `no_data` with bounded diagnostics |
| Multiple cohorts exist for one stock | Select one deterministic coherent cohort |
| Close is null, non-positive, NaN, or infinite | Exclude the observation; never fabricate a value |
| Database/API request fails | Preserve failure; page renders localized error, not empty data |

### 5. Good / Base / Bad Cases

- Good: four stocks share 63 `akshare/qfq` dates; every chart and matrix cell
  uses those same 63 observations and one first-date baseline.
- Base: one selected code is unavailable while two others remain comparable;
  the page shows the missing code and renders the valid comparison.
- Bad: fetch missing bars on page load, mix raw and forward-adjusted rows,
  correlate pairwise date subsets, replace a missing code with a search hit, or
  hide API failure behind an empty state.

### 6. Tests Required

- Service tests cover normalization/order, database-only search, exact
  identity, missing-symbol preservation, coherent cohort choice, period
  anchoring, finite-number filtering, exact shared dates, and every state.
- API tests cover enum/length/count bounds, comma-separated delegation, and
  the injected session.
- Utility tests prove normalization and correlations use only exact shared
  dates and one shared baseline.
- Page tests prove GET-only loading, URL-owned add/remove/period/search state,
  provenance, exact detail links, hidden duplicate selection controls, and
  distinct empty/insufficient/no-data/error branches.
- Instruments tests prove ordinary list loading issues no `/bars` comparison
  request. Browser acceptance covers desktop and `390x844` without horizontal
  page overflow.

### 7. Wrong vs Correct

#### Wrong

```python
bars = get_market_data(symbol)  # may call a provider
series = sorted(raw_bars + adjusted_bars, key=lambda row: row.trade_date)
```

This makes a read page mutable/network-dependent and combines incompatible
price bases.

#### Correct

```python
rows = query_stored_daily_bars(session, selected_ids, period_start, anchor_date)
cohort = choose_largest_provider_adjustment_cohort(rows)
shared_dates = set.intersection(*(dates(item) for item in comparable_items))
```

The data boundary, price basis, and observation window remain deterministic
and auditable.
