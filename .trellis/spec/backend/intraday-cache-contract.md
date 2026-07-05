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
