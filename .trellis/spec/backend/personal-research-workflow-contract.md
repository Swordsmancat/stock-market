# Personal Research Identity and Financial State Contract

## Scenario: Exact Instrument Watch State and Trustworthy Presentation

### 1. Scope / Trigger

- Trigger: a personal user moves from search, the daily shortlist, instruments,
  or watchlist into one exact instrument detail page and reviews or changes its
  watch state.
- Scope: instrument links and detail query parameters, exact instrument
  identity resolution, read-only watchlist membership, detail watch/unwatch,
  watchlist load-state and currency presentation, and missing detail values.
- Non-goals: homepage changes, report generation, alert evaluation, portfolio
  or trading features, watchlist maintenance panels, or automatic enrichment.

### 2. Signatures

- Service read:
  `get_watchlist_item_membership(symbol: str, market: str, session: Session) -> dict[str, object]`.
- FastAPI read: `GET /watchlist/items?symbol=<symbol>&market=<market>`.
- FastAPI write input: `WatchlistItemInput.alert_rules: dict[str, Any] | None`;
  omission means preserve an existing row's rules, while an explicit `{}` means
  clear them.
- Web identity read:
  `fetchInstrumentDetailContext(symbol, market?) -> { identity, watchlistMembership }`.
- Detail query values accept `string | string[] | undefined`; the page uses the
  first value and trims it before calling services or rendering snapshot state.
- Watchlist page fetch returns a discriminated `loaded | failed` result.

### 3. Contracts

- Watchlist identity is the normalized pair `(symbol, market)`. Known source
  links preserve `market`; detail lookup may use a bounded exact fallback but
  never guesses when the same symbol resolves to multiple markets.
- Membership reads query the existing default watchlist and exact item
  directly. They do not create/seed the default list, call enriched watchlist
  serialization, fetch prices, evaluate alerts, write alert history, or commit.
- No exact identity or a failed membership read produces
  `watchlistMembership="unavailable"`; the detail toggle is disabled.
- The detail client uses the same-origin `/api/watchlist/items` POST/DELETE
  proxy, keeps the current URL, shows pending/success/error feedback, and calls
  `router.refresh()` after success. It exposes no report or maintenance action.
- Re-adding a soft-removed row without `alert_rules` preserves its existing
  alert rules. Explicit rule payloads continue to replace them.
- Watchlist transport/HTTP/JSON failure renders `ErrorState` plus a localized
  reload action. Only a successful payload with zero items renders the existing
  empty state and zero-item metrics.
- Watchlist numeric prices map `CN -> CNY`, `HK -> HKD`, and `US -> USD`.
  Unknown markets use locale number formatting without a guessed currency.
- Missing detail latest price, change, or percent change renders the localized
  unavailable label and no movement color. Never synthesize `0.00`, `+0.00`, or
  `+0.00%` for absent values.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Blank membership symbol or market | HTTP 400; no database mutation |
| Default watchlist absent | HTTP 200 `not_watched`; no list/item rows created |
| Exact active item exists | HTTP 200 `watched` with the exact serialized item |
| Same symbol, different market | `not_watched`; do not cross-match |
| Identity lookup is ambiguous or fails | Detail toggle disabled as `unavailable` |
| Membership read fails | Exact identity may render, but mutation remains disabled |
| Re-add omits `alert_rules` | Reactivate while preserving stored rules |
| Re-add sends explicit `{}` | Reactivate and clear stored rules |
| Watchlist request fails | Error state and reload action; no empty KPI projection |
| Watchlist request succeeds with `items=[]` | Genuine empty state |
| Price/change value is absent | Localized unavailable value; no synthetic zero |

### 5. Good / Base / Bad Cases

- Good: a `0700` HK link reaches `?market=HK`, resolves one exact instrument,
  reads membership without writes, and toggles the same row without navigation.
- Good: an item with alert rules is removed and later re-added from detail; the
  rules remain intact because the compact toggle omits `alert_rules`.
- Base: no default watchlist exists; the detail control shows Add while the
  membership read leaves the database untouched.
- Base: a successful empty list shows the existing personal empty state.
- Bad: a GET membership check seeds defaults, enriches prices, evaluates alerts,
  commits alert history, or treats a provider failure as an empty watchlist.
- Bad: a CN value uses USD, an unknown market guesses CNY, or missing detail data
  is displayed as a real zero.

### 6. Tests Required

- Service tests assert absent-list reads create no rows, exact market matching,
  soft-removed behavior, zero alert-history writes, and rule preservation on
  omitted re-add payloads.
- API tests assert exact GET payloads, blank-input HTTP 400 behavior, and no
  mutation from membership reads.
- Next proxy tests assert method, exact forwarded query/body, no-store behavior,
  upstream status, content type, and payload propagation.
- Component/page tests assert toggle pending/success/error/unavailable states,
  same-page refresh, repeated-query normalization, failed-versus-empty watchlist
  branches, CN/HK/US currencies, and unavailable detail values.
- Browser acceptance checks desktop and `375x812` layouts for horizontal
  overflow and verifies exact search/detail navigation when browser policy
  permits interaction.

### 7. Wrong vs Correct

#### Wrong

```python
payload = get_default_watchlist_payload(session=session)
watched = any(item["symbol"] == symbol for item in payload["items"])
```

This read may seed defaults, enrich prices, evaluate alerts, and ignores market
identity.

#### Correct

```python
membership = get_watchlist_item_membership(
    symbol=symbol,
    market=market,
    session=session,
)
```

The direct exact query is side-effect free and keeps unavailable/empty/watched
states distinct.

## Scenario: Market-Aware CN Daily-Bar Source Fallback

### 1. Scope / Trigger

- Trigger: a personal user opens a searched instrument detail page or requests
  AI analysis and stored daily bars are empty or severely sparse, or the
  requested daily-bar provider returns no rows, raises, is rate-limited, or
  returns malformed rows.
- Scope: canonical search identity, daily bars/latest/indicators APIs,
  database-first reads, CN provider coordination, detail provenance, and the
  market assistant's daily-bar context.
- Non-goals: intraday/depth fallback, index-to-stock guessing, mock recovery,
  HK/US fallback through CN providers, provider backfill, or trading actions.

### 2. Signatures

- Bars API:
  `GET /market-data/{symbol}/bars?timeframe=1d&start=YYYY-MM-DD&end=YYYY-MM-DD&provider=<name>&market=CN`.
- Latest/indicator APIs accept the same optional `market` query and forward it
  to `get_latest_bar_payload(...)` / `get_indicator_payload(...)`.
- Service:
  `get_bars_payload(symbol, timeframe, start, end, session=None, provider_name=None, market=None)`.
- Assistant request/service adds optional `market`; detail sends the daily-bar
  effective provider plus the exact resolved market.
- Coordinator:
  `DailyBarFetchCoordinator.fetch(symbol, timeframe, start, end, policy="cn_resilient")`.
- Tushare may be configured by stored `tushare_token` or `TUSHARE_TOKEN`; both
  enable the same fallback source.

### 3. Contracts

- Database daily bars remain first. When market is known, lookup identity is
  `(Market.code, Instrument.symbol)`; another market's same symbol cannot win.
- For an exact CN six-digit stock daily range, severe sparsity is measured as
  `min(35, max(1, ceil(requested_weekday_count / 2)))`. Weekdays are calculated
  arithmetically from the requested dates; this detector does not claim trading-
  calendar completeness or require weekend/holiday boundary rows.
- A coherent database cohort meeting that minimum remains a zero-network hit.
  A smaller non-empty cohort is retained as the degraded fallback while the
  existing CN resilient coordinator runs with the same `minimum_row_count`.
  Remote providers and adjustments are never stitched, and GET never writes
  recovered bars.
- A database response contains only the latest continuous cohort with one
  effective `(provider, source, adjustment)` identity. Dropped earlier cohorts
  produce `status="degraded"` and `MIXED_DAILY_BAR_PROVENANCE`; incomplete
  legacy provenance produces `UNKNOWN_DAILY_BAR_PROVENANCE` and never invents
  an adapter provider. Legacy `tushare.pro.daily + qfq` is corrected to `raw`
  through the shared adjustment resolver.
- The latest-bar database path preserves those diagnostics with a latest-row,
  provenance-boundary, and dropped-row count query. It must not materialize the
  symbol's full daily-bar history because watchlist batch enrichment calls this
  path once per symbol.
- Resilient fallback is eligible only for exact `market="CN"`,
  `timeframe="1d"`, a six-digit numeric stock symbol, and a non-mock requested
  provider. The ordered sources are:

```text
requested provider
  -> akshare.stock_zh_a_hist (qfq)
  -> akshare.stock_zh_a_daily (qfq)
  -> tushare.pro.daily (raw)
```

- Each source is attempted at most once. Unconfigured alternates remain visible
  as `skipped_unconfigured` and are not called. Mock is never appended.
- A whole source is selected only after validating row type, symbol, date
  range, duplicate dates, Decimal field structure, finite OHLCV/amount,
  consistent OHLC, and non-negative volume. Selected rows are sorted ascending;
  rows from different sources or adjustments are never merged.
- Provider/schema/rate/dependency failures reach the coordinator. Attempts may
  expose only `provider`, `source`, `status`, `row_count`, validation `code`,
  and `exception_type`; exception messages, URLs, tokens, and response bodies
  are forbidden.
- Payload provenance is additive:
  `requested_provider`, `effective_provider`, `provider`, `source`,
  `upstream_source`, `adjustment`, `provenance_known`,
  `provenance_corrected`, `fallback_used`, `source_attempts`, `diagnostics`,
  `status`, and `no_data_reason`.
- Successful alternate selection returns `status="ok"`. All configured sources
  returning empty is `no_data`; any failed/invalid source with no selected rows
  is `degraded`. Latest, indicators, and assistant context preserve that state.
- When severe-sparsity recovery exhausts all remote sources, return the retained
  non-empty database cohort with sanitized source attempts, `status="degraded"`,
  and `INSUFFICIENT_DATABASE_COVERAGE`; never replace useful stored evidence
  with an empty response.
- Intraday previous-close resolution keeps its direct database reference. When
  that reference exists, a minute request must not re-enter sparse daily-bar
  recovery; only a missing stored reference may use the provider-backed daily
  path. This preserves intraday behavior and prevents new page-load fan-out.
- Detail fetches daily bars once and derives latest from the same payload,
  including the empty/degraded state. It does not run a second fallback chain.
- Search resolves an exact market before navigation when one unique exact
  result exists. Provider-specific logical index symbols omit `market=CN` from
  daily and assistant requests so numeric index codes cannot enter stock
  fallback.
- Detail and AI use the daily-bar effective provider, never market-depth
  provenance. Unsupported/storage provider labels fall back to the requested
  adapter. Requested/effective differences show a localized source notice;
  stable diagnostics render localized code text rather than backend messages.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| CN 1d primary succeeds | Select primary once; `fallback_used=false` |
| Primary empty/fails/malformed | Continue in exact priority order |
| AkShare hist fails, daily succeeds | Select `stock_zh_a_daily`; sanitized attempts |
| AkShare unavailable, Tushare succeeds | Select `tushare.pro.daily`, `adjustment=raw` |
| `TUSHARE_TOKEN` only | Tushare is configured and eligible |
| Tushare dependency/rate/schema failure | Record failed `exception_type`; continue/exhaust degraded |
| All configured sources empty | `no_data`, empty items, no mock |
| At least one source fails/invalid and none succeeds | `degraded`, empty items, no mock |
| HK/US/missing market or non-1d | Existing single-provider behavior; no CN alternate |
| Provider-specific logical index | Omit CN market forwarding; no stock fallback |
| DB range crosses provenance cohorts | Return latest continuous cohort and degraded diagnostic |
| Coherent exact-CN DB cohort meets severe-sparsity minimum | Return database immediately; zero provider calls |
| Coherent exact-CN DB cohort is below the minimum | Run the resilient coordinator with that minimum row count |
| Sparse DB recovery exhausts remote sources | Return retained DB cohort with `INSUFFICIENT_DATABASE_COVERAGE` |
| Intraday request has a stored previous close | Reuse it; zero daily coordinator calls |
| Legacy DB provenance unknown | Effective provider remains null; never pass `database` as adapter |
| Latest provenance-boundary audit fails | Return degraded unknown-provenance diagnostics; never assume a coherent series |
| Assistant receives degraded empty bars | No LLM call; `SOURCE_UNAVAILABLE`, not `SOURCE_NO_DATA` |

### 5. Good / Base / Bad Cases

- Good: searching `920000` resolves `market=CN`; yfinance and AkShare hist do
  not yield usable rows, AkShare daily succeeds, detail shows its exact source,
  and AI cites the same daily-bar provider.
- Good: a stored qfq cohort follows older raw rows; detail uses only the latest
  continuous cohort, marks degraded, and AI receives the diagnostic.
- Good: one stored row exists in a multi-week exact-CN request; the first
  validated remote source meeting half the requested weekdays replaces only
  the response projection.
- Base: a US symbol has no yfinance rows; it remains explicit no-data and never
  calls AkShare/Tushare.
- Bad: convert provider exceptions to empty frames, mix raw/qfq rows, launch
  `/latest` and `/bars` fallback chains together, infer CN from a numeric symbol,
  accept any non-empty sparse database cohort as sufficient, pass `database`
  as an assistant adapter, or render raw exception text.

### 6. Tests Required

- Coordinator tests cover structural/numeric malformed rows, non-finite amount,
  symbol mismatch, ordering, sanitized attempts, configured skips, and strict
  policy not calling alternates.
- Provider tests cover yfinance CN/HK/BSE ticker mapping, shared Tushare
  SH/SZ/BJ mapping, one `pro.daily` call, missing dependency, upstream failure,
  schema failure, and true empty frames.
- Service tests cover four-source priority, no mock, all-empty versus failed
  exhaustion, env-only Tushare, market-scoped DB reads, latest continuous DB
  cohort, severe-sparsity threshold boundaries, remote recovery and retained
  database exhaustion, non-CN/short-range compatibility, legacy adjustment
  correction, latest/indicator provenance, intraday stored-close reuse with
  zero daily-provider calls, and a latest-bar regression that forbids the full-
  history range helper. Boundary audit query failures remain explicitly
  degraded.
- API tests assert optional market forwarding for bars/latest/indicators and
  assistant requests.
- Frontend tests assert immediate search submit retains a unique market, index
  market omission, one daily fallback chain per detail load, derived latest
  provenance, source notice behavior, provider filtering, and localized
  diagnostics without raw backend messages.
- Live acceptance uses an isolated Compose project and proves primary empty or
  failed, a later source selected, normal `3000/8000` health unchanged, and no
  secret present in evidence/log output.

### 7. Wrong vs Correct

#### Wrong

```python
bars = requested.fetch_bars(symbol, "1d", start, end)
if not bars:
    bars = MockProvider().fetch_bars(symbol, "1d", start, end)
```

This fabricates evidence, hides the actual source gap, and can contaminate AI
analysis.

#### Correct

```python
result = coordinator.fetch(
    symbol,
    "1d",
    start,
    end,
    policy=CN_RESILIENT_POLICY,
    minimum_row_count=severe_sparsity_minimum(start, end),
)
```

The coordinator selects one validated configured source, preserves sanitized
provenance, and returns explicit no-data/degraded state when none succeeds.

## Scenario: Mixed-Provenance Daily Recovery

### 1. Scope / Trigger

- Trigger: a CN daily-bar read finds a research-ready stored range, but mixed
  provider/source/adjustment provenance leaves the newest coherent cohort too
  short for personal research.
- Non-goals: writing recovered bars, stitching sources, changing readiness
  thresholds, backfill, or non-CN fallback.

### 2. Signatures

- Existing bars API and service signatures remain unchanged.
- `DailyBarFetchCoordinator.fetch(...)` accepts additive
  `required_coverage: tuple[date, date] | None` and
  `minimum_row_count: int | None`.

### 3. Contracts

- A coherent database cohort meeting the severe-sparsity minimum remains
  authoritative and triggers no provider request.
- A mixed, research-ready stored range may run the existing CN resilient
  coordinator with the full stored date range as required coverage. This
  mixed-provenance recovery takes precedence over the weaker sparse-cohort
  branch and keeps the original stored row count as its minimum.
- `minimum_row_count` checks candidate count only. First/last date boundaries
  are enforced only when `required_coverage` is supplied, so a sparse coherent
  request whose dates fall on weekends or holidays is not rejected solely for
  missing those boundary dates.
- A remote candidate outside the required start/end coverage is recorded as
  `insufficient_coverage`; the coordinator continues without merging rows.
- A boundary-spanning remote candidate is still insufficient when it contains
  fewer rows than the complete mixed stored range. Recovery passes the original
  stored row count as `minimum_row_count`; it never substitutes the fixed
  35-row research-readiness threshold for completeness.
- The first complete validated remote series replaces the projection for that
  response only. GET remains read-only.
- Exhaustion returns the prior non-empty coherent database cohort as degraded,
  including mixed-provenance diagnostics and sanitized source attempts.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Coherent stored cohort meets severe-sparsity minimum | Return database immediately |
| Mixed stored range below recovery threshold | Keep current coherent cohort |
| Primary remote misses required boundary | `insufficient_coverage`; continue |
| Primary spans boundaries but has fewer rows than stored range | `insufficient_coverage`; continue |
| Later remote covers and validates | Return that source only, `status="ok"` |
| Every remote empty/invalid/failed/short | Return prior database cohort, degraded |
| Any remote response contains mixed/invalid rows | Reject the whole candidate |

### 5. Good / Base / Bad Cases

- Good: a two-row newest cohort over 60 stored rows rejects a sparse
  boundary-spanning 35-row source, then selects a complete 60-row AkShare
  series without changing the database.
- Base: a sufficient coherent stored series remains a zero-network database hit.
- Bad: accept a sparse latest-only remote result, merge qfq/raw rows, or return
  an empty payload after recovery exhaustion.

### 6. Tests Required

- Coordinator tests assert insufficient coverage continues in exact order and
  attempts expose no exception messages or provider bodies. A dedicated test
  must prove first/last-date coverage alone cannot satisfy a larger
  `minimum_row_count`.
- Service tests assert complete recovery, read-only row count, and preservation
  of the degraded non-empty cohort when all remote candidates fail.
- Existing latest/indicator/assistant provenance tests remain green.

### 7. Wrong vs Correct

#### Wrong

```python
if database_is_mixed:
    return remote_rows or []
```

#### Correct

```python
result = coordinator.fetch(
    ...,
    required_coverage=(stored_start, stored_end),
    minimum_row_count=stored_row_count,
)
return serialize(result.bars) if result.bars else degraded_database_payload
```

---

## Scenario: Bounded CN Homepage Index Fallback

### 1. Scope / Trigger

- Trigger: the homepage requests a configured CN market index through
  yfinance and the complete primary daily-bar result is empty or invalid.
- Scope: homepage market-index serialization and AkShare's public Sina index
  daily adapter.
- Non-goals: followed stocks, HK/US indices, database writes, row stitching,
  Cookie/login access, generic crawling, or research-threshold changes.

### 2. Signatures

- Provider: `AkShareProvider.fetch_index_bars(symbol, start, end) -> list[ProviderBar]`.
- Downloader: `AkShareProvider.download_sina_index_daily_bars(symbol, start, end) -> DataFrame`.
- Service boundary: `_serialize_market_index(index, session, provider_name, start, end, today)`.

### 3. Contracts

- Yfinance remains primary. Only `index.market == "CN"` and requested provider
  `yfinance` are eligible for one Sina fallback call.
- Sina symbols use `sz` for `399*` index codes and `sh` otherwise. Returned
  rows are bounded to the requested dates and require finite OHLCV plus valid
  OHLC ordering and non-negative volume.
- One complete source wins; primary and fallback rows are never merged.
- Fallback success reports provider/effective provider `akshare`, source
  `akshare.stock_zh_index_daily`, and requested provider `yfinance`.
- Empty fallback is `no_data`. Failure is sanitized `unavailable` with only the
  provider and exception type in diagnostics. There is no retry or persistence.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Valid finite yfinance payload | Return unchanged; zero Sina calls |
| Empty or non-finite CN yfinance payload | Make exactly one Sina call |
| Valid Sina rows | Return only Sina rows with truthful attribution |
| Empty Sina frame | Explicit `no_data`; no retry |
| Sina schema/network failure | Sanitized `unavailable`; no raw message |
| Non-CN index or non-yfinance request | Never call Sina |

### 5. Good / Base / Bad Cases

- Good: ChiNext yfinance returns no rows, Sina returns one coherent requested
  range, and the homepage displays it as AkShare/Sina evidence.
- Base: both sources are empty, so the card remains explicit no-data.
- Bad: combine stale yfinance rows with fresh Sina rows, expose an upstream URL
  in diagnostics, or use the stock fallback coordinator for an index.

### 6. Tests Required

- Provider tests assert `sz399006`/`sh000905` mapping, date bounding, invalid
  row rejection, and normalized `ProviderBar` identity.
- Service tests assert zero-call primary success, exactly-one-call empty and
  invalid fallback, coherent-source attribution, empty fallback, sanitized
  failure, and non-CN exclusion.
- Market overview cache and API concurrency regressions remain green.

### 7. Wrong vs Correct

#### Wrong

```python
bars = yfinance_bars + akshare_bars
```

#### Correct

```python
if primary_is_complete_and_finite(primary):
    return primary
return fetch_sina_index_once(index)
```
