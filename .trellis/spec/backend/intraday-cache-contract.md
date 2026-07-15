# Intraday Minute Cache Contract

## Scenario: Historical Closed-Session Minute Cache

### 1. Scope / Trigger

- Trigger: `GET /market-data/{symbol}/intraday?date=YYYY-MM-DD&timeframe=1m` now persists and reuses verified provider-returned minute bars for historical closed sessions.
- Scope: backend service logic in `packages/services/market_data.py`, provider intraday adapters in `packages/providers/base.py`, ORM models in `packages/domain/models.py`, Alembic migrations, and API/service tests.
- Non-goals: realtime streaming, current-session cache reuse, full global exchange calendars, half-day handling, pre/post-market sessions, and synthetic minute generation.

### 2. Signatures

- API: `GET /market-data/{symbol}/intraday?date=YYYY-MM-DD&timeframe=1m&provider=<provider>`
- Service: `get_intraday_bars_payload(symbol, trade_date, timeframe="1m", session=None, provider_name=None)`
- Provider method: `fetch_intraday_bars(symbol: str, trade_date: date, timeframe: str) -> list[ProviderIntradayBar]`
- Fact table: `bars_1m(instrument_id, ts, open, high, low, close, volume, amount)`
- Cache metadata table: `intraday_minute_cache_entries(provider, symbol, trade_date, timeframe, instrument_id, source, row_count, first_ts, last_ts, fetched_at, cached_at)`

### 3. Contracts

- Only explicit provider intraday methods may produce minute `items`.
- Historical closed sessions may read from persistent cache before provider calls.
- Current sessions stay provider-first and must not return cached rows as realtime data.
- `source="provider"` means rows came from a provider fetch in this request.
- `source="cache"` means rows came from `bars_1m` after matching `intraday_minute_cache_entries`.
- `source="none"` is used for unsupported providers and session-policy skips.
- `freshness.cache_status` values:
  - `hit`: historical closed-session cache hit; provider was not called.
  - `miss`: cache was checked and missed, then provider path ran.
  - `skipped`: session/provider policy deliberately skipped cache or provider work.
  - `unavailable`: no DB session or cache read/write failed; provider data may still be returned.
- `session.status` must be present on `ok`, `no_data`, and `degraded` payloads.

### 4. Validation & Error Matrix

- Unsupported timeframe -> `ValueError`, mapped by router to HTTP 400.
- Provider without `fetch_intraday_bars` -> HTTP 200 payload with `status="degraded"`, `source="none"`, `freshness.cache_status="skipped"`.
- Future date, weekend, or known yfinance US-like holiday -> HTTP 200 `status="no_data"`, `source="none"`, `freshness.cache_status="skipped"`, no provider data calls.
- Historical closed-session cache hit -> HTTP 200 `status="ok"`, `source="cache"`, `freshness.cache_status="hit"`, no provider calls.
- Historical closed-session cache miss -> provider fetch; verified rows are persisted; response has `source="provider"` and `freshness.cache_status="miss"`.
- Cache read/write failure -> rollback session when possible; return provider data with `freshness.cache_status="unavailable"` instead of failing a usable provider response.
- Provider empty response -> `status="no_data"`; do not write fake `bars_1m` rows or cache metadata.

### 5. Good/Base/Bad Cases

- Good: yfinance returns verified rows for `AAPL` on a historical trading day; service writes `bars_1m` plus `intraday_minute_cache_entries`; the second request returns `source="cache"`.
- Base: yfinance returns no rows for a valid historical date; service returns `no_data` and leaves minute cache empty.
- Bad: weekend request calls yfinance daily or minute APIs to calculate a reference line. This violates session governance; use database-only previous close if available.
- Bad: unsupported provider falls back to daily `fetch_bars("1m")`. This fabricates minute data and is forbidden.

### 6. Tests Required

- Service test for provider fetch -> cache write -> repeated cache hit without provider calls.
- API test proving the router passes a real DB session and the second request returns `source="cache"`.
- Session-policy tests for future/weekend/holiday paths asserting no daily or minute provider calls.
- Unsupported provider tests asserting `degraded`, `session`, and `freshness.cache_status="skipped"`.
- Migration test proving `intraday_minute_cache_entries` is created with provider/symbol/date/timeframe metadata columns.
- Cache-unavailable test proving provider rows are still returned with `freshness.cache_status="unavailable"`.

### 7. Wrong vs Correct

#### Wrong

```python
# Do not fabricate minute rows from daily bars or mock fixtures.
bars = provider.fetch_bars(symbol, "1m", trade_date, trade_date)
return {"status": "ok", "items": [serialize_bar(bar) for bar in bars]}
```

#### Correct

```python
if session_status == "closed_session":
    cached = _get_intraday_cache_lookup(...)
    if cached.status == "hit":
        return _build_intraday_ok_payload(source="cache", cache_status="hit", ...)

provider_rows = provider.fetch_intraday_bars(symbol, trade_date, "1m")
_persist_intraday_cache_bars(..., bars=provider_rows)
```

## Scenario: Market-Aware CN Intraday Fallback

### 1. Scope / Trigger

- Trigger: an exact CN stock detail asks for one-minute bars and its requested
  provider is empty, unsupported, malformed, or unavailable.
- Non-goals: realtime streaming, Tushare minute entitlement, index guessing,
  depth fabrication, or daily-to-minute synthesis.

### 2. Signatures

- API:
  `GET /market-data/{symbol}/intraday?date=YYYY-MM-DD&timeframe=1m&provider=<provider>&market=CN`.
- Service:
  `get_intraday_bars_payload(..., provider_name=None, market=None)`.
- Web detail forwards the exact resolved market unless it uses a
  provider-specific logical index symbol.
- Cache identity constraint:
  `UNIQUE(instrument_id, provider, symbol, trade_date, timeframe)`, introduced
  by `0023_intraday_cache_market_identity`.

### 3. Contracts

- Keep future/weekend/known-holiday short circuits and historical closed-session
  cache reads ahead of every provider call.
- The fixed provider order is requested provider, AkShare
  `stock_zh_a_hist_min_em`, then AkShare `stock_zh_a_minute`. Each source is
  attempted at most once and there is no retry or synthetic minute data.
- Normalize naive AkShare timestamps as `Asia/Shanghai`, filter the exact trade
  date, and validate symbol, ordering, duplicates, finite OHLC/amount, OHLC
  consistency, and non-negative volume before selecting a whole source.
- A selected source cannot mix naive and timezone-aware timestamps. Mixed
  awareness is `MIXED_INTRADAY_TIMESTAMP_AWARENESS`, records an invalid source
  attempt, and continues the fallback chain instead of leaking a sort error.
- Successful fallback returns `status="ok"`, exact requested/effective provider,
  upstream source, `fallback_used=true`, and sanitized source attempts. All
  executable sources returning empty is `no_data`; any provider/schema failure
  with no selected source is `degraded`.
- HK, US, mock, ambiguous, and provider-specific index identities stay on the
  existing single-provider path and never enter the CN source chain. AkShare's
  A-share minute methods are also reported unsupported for those identities and
  must receive zero calls.
- A historical cache lookup is provider-agnostic after resolving the exact
  instrument, symbol, market, date, and timeframe. It must find a valid cached
  source even when the requested provider changes or the provider that wrote
  the cache is no longer enabled. The cache entry's provider/source remain the
  effective provenance in the response.
- Cache lookup and cleanup remain scoped to exact market/instrument identity.
  The provider-agnostic `bars_1m` facts may have only one matching provider
  metadata owner per exact instrument/symbol/date/timeframe. A successful
  source switch removes conflicting metadata for that instrument before commit;
  another market's same numeric code is neither reused nor deleted.
- CN and HK cache metadata with the same provider/symbol/date/timeframe may
  coexist because `instrument_id` participates in uniqueness. Downgrade to the
  legacy constraint must refuse before DDL when such rows exist; it must not
  delete a valid market cache to force rollback.
- Cache reads and writes preserve `source`, freshness timestamps, row count,
  first/last timestamps, and rollback-to-provider behavior on database errors.

### 4. Validation & Error Matrix

| Condition | Required behavior |
| --- | --- |
| Future/weekend/known holiday | `no_data`; zero provider calls |
| Closed-session exact cache hit | `ok`, `source="cache"`; zero provider calls |
| Requested provider succeeds | Select it once; `fallback_used=false` |
| Requested source empty/unsupported/fails | Continue in fixed CN order |
| AkShare EM empty, Sina succeeds | Select `stock_zh_a_minute` only |
| One source mixes naive/aware timestamps | Record invalid stable code; continue |
| Every executable source empty | `no_data` |
| Any source fails/invalid and none succeeds | `degraded` |
| Non-CN, mock, non-six-digit, or logical index | Existing single-provider path |
| Non-CN request selects AkShare | Unsupported; zero A-share minute calls |
| Same code cached under two exact markets | Both persist and hit independently |
| Migration downgrade sees a legacy-key collision | Abort before changing constraints |
| Cache database operation fails | Roll back; preserve usable provider rows |

### 5. Good / Base / Bad Cases

- Good: yfinance is empty, AkShare EM succeeds, its rows are cached under the
  exact CN instrument, and the second yfinance-requested read hits that cache.
- Good: CN and HK instruments share a numeric code and independently retain
  their own minute facts and metadata.
- Base: all providers legitimately return empty and the UI sees `no_data`.
- Bad: infer CN from digits alone, reuse another market's cache entry, call a
  provider on a holiday, or fabricate minutes from daily bars.

### 6. Tests Required

- Provider tests cover EM/Sina field normalization, BSE/SH/SZ prefixes, exact
  date filtering, Asia/Shanghai timestamps, empty frames, and malformed schema.
- Service tests cover priority, attempts, all-empty versus failed exhaustion,
  fallback cache reuse, exact-market cache isolation, metadata replacement,
  mixed timestamp awareness, non-CN AkShare exclusion, and database-error
  rollback. Cache regressions must also cover a yfinance-written entry requested
  through AkShare/Tushare and a disabled-AkShare entry requested through another
  provider.
- Model/migration tests assert `instrument_id` is part of the cache unique key,
  exact-market rows coexist, and ambiguous downgrade is rejected without DDL.
- API and Web tests assert optional market forwarding and logical-index
  exclusion. Existing depth no-fabrication tests remain green.

### 7. Wrong vs Correct

#### Wrong

```python
bars = provider.fetch_bars(symbol, "1m", trade_date, trade_date)
```

#### Correct

```python
result = fetch_cn_intraday_sources(
    symbol=symbol,
    market="CN",
    sources=(requested, akshare_em, akshare_sina),
)
```
