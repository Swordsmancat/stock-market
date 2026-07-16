# Stabilize homepage market and news availability

## Goal

Make the personal homepage truthfully show available market-index values and
keep stored news readable during a cold market-overview load, without widening
the product surface or hiding genuine macro-data gaps.

## Background

- The homepage reproduces missing values for Shanghai Composite, Shenzhen
  Component, and CSI 300 while labeling them `status="ok"` and `fresh`.
- The raw CSI 300 daily payload contains a final row dated 2026-07-15 with
  volume but null OHLC values. `YFinanceProvider.fetch_bars()` currently turns
  non-finite values into `ProviderBar` rows instead of rejecting the row.
- `get_market_overview_payload()` aggregates ten indices and is cached for 300
  seconds. A contradictory successful payload can therefore survive multiple
  page loads.
- `GET /dashboard/market-overview` is declared async but directly executes
  synchronous database/provider work. During a cold overview request, a stored
  `GET /news/latest?limit=6` probe took 6256 ms; the same endpoint in isolation
  completed 20 samples in 13-79 ms. The homepage optional-news timeout is 5000
  ms, so the blocked request renders a false news failure.
- Missing macro observations are real source/seed gaps and are not caused by
  this defect.

## Requirements

### R1. Finite daily-bar provider boundary

- YFinance daily bars must require finite Open, High, Low, Close, and Volume
  values for every emitted row.
- A partially populated or non-finite row is skipped as unusable. Valid rows in
  the same response remain available in chronological order.
- A response containing no valid rows remains explicit no-data; no price is
  fabricated and no prior close is copied into the invalid date.

### R2. Truthful market-overview caching

- A market-overview payload must not be cached when any `status="ok"` followed
  instrument or index lacks a finite numeric `latest.close`.
- Valid `ok`, explicit `no_data`, and explicit `unavailable` sections remain
  cacheable under the existing provider/date key and 300-second TTL.
- The response contract remains compatible; no frontend field or route changes.

### R3. Non-blocking cold overview

- The synchronous market-overview service must run through FastAPI's sync route
  execution boundary instead of blocking the event loop.
- A concurrent stored-news GET must complete independently while a cold
  market-overview service call is waiting.
- Do not mask the defect by increasing the homepage news timeout or by adding
  retries/fan-out.

### R4. Scope and compatibility

- Keep the homepage news endpoint read-only and database-backed.
- Preserve the normal 3000/8000 stack, current provider/source attribution,
  market-overview response schema, and existing 95/90/80 research gates.
- Preserve unrelated five-day acceptance, yfinance worktree metadata,
  feasibility-task files, and `.codex-worktrees`.
- Do not add macro adapters, login/Cookie access, generic crawling, trading
  actions, or a new homepage module.

### R5. Bounded A-share index fallback

- Keep yfinance as the primary source for every configured market index.
- Only when a yfinance result for a CN index is empty or invalid, make one
  fallback attempt through AkShare's public Sina index-daily endpoint.
- Select one complete source response. Never stitch yfinance and Sina rows,
  and never write fallback rows to the database.
- A successful fallback must report `provider="akshare"`, the Sina index
  source, `requested_provider="yfinance"`, and
  `effective_provider="akshare"`.
- An empty or failed Sina response remains explicit no-data or unavailable;
  do not retry, fabricate values, use Cookie/login state, or widen the fallback
  to non-CN indices or followed stocks.

### R6. Docker Desktop full-stack availability

- The default Compose project must include the Next.js web service, expose it
  on host port 3000, and expose the API on host port 8000.
- Container-side SSR requests use the Compose API hostname; browser-side
  requests use the host-published API URL.
- Database, Redis, API, worker, Beat, and web services restart after Docker
  Desktop restarts and respect dependency health before starting consumers.
- Keep the isolated acceptance Compose ports and project unchanged.

## Acceptance Criteria

- [x] A YFinance frame with valid rows plus a non-finite final row returns only
      the valid rows; the latest close is finite and comes from the last valid
      trading date.
- [x] A contradictory `ok` market-overview result is returned but not cached;
      the next call recomputes instead of replaying it.
- [x] A valid market-overview result remains cached with the existing key/TTL.
- [x] An ASGI concurrency regression proves stored news completes before a
      deliberately slow cold market-overview call.
- [x] Existing provider, dashboard, news API, homepage, Ruff/type checks, and
      relevant Python/Next.js regressions pass.
- [x] After reload and cache invalidation, 3000/8000 are healthy, homepage news
      loads, and configured A-share index cards never claim `fresh`/`ok` with a
      missing price.
- [x] A valid yfinance CN-index result makes zero Sina calls; an empty or
      invalid primary result makes exactly one Sina call and uses only its
      normalized finite rows with truthful source attribution.
- [x] An empty or failed Sina fallback stays truthful and sanitized, without
      retries, row stitching, database writes, or impact on non-CN indices.
- [x] `docker compose config` includes `web`, maps `3000:3000`, and resolves
      healthy dependency ordering without changing acceptance-stack ports.
- [x] A clean default Compose start makes `/health` available on 8000 and the
      localized homepage available on 3000 without a separate host-side Next
      process.

## Out Of Scope

- Changing the configured primary provider order or adding a generic
  multi-provider index coordinator beyond the bounded yfinance-to-Sina rule.
- Filling missing macro observations.
- Changing homepage layout, copy, timeouts, or retry policy.
