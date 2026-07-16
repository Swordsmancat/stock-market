# Harden public research data fallbacks

## Goal

Make A-share detail data recover automatically from severe stored daily-bar
sparsity and make public news refresh bounded, schema-validated, Cookie-free,
and truthfully attributed, without adding login state or broad crawling.

## Background

- The existing CN daily-bar coordinator already provides a validated fallback
  order, but `get_bars_payload` returns any non-empty coherent database cohort.
  A 2026-06-01 through 2026-07-16 probe for `600519` therefore returned one
  degraded database row and made zero source attempts, while an explicit public
  fallback returned 117 coherent rows.
- News refresh is already database-first, one-shot, sequential, and
  stop-on-first-persisted-success. The normal database currently has 20 rows
  for only two symbols, so arbitrary detail pages still begin from a cold store.
- AkShare 1.18.64 implements `stock_news_em` with a bundled static Cookie and
  an unbounded `requests.get`. Both the detail refresh adapter and the legacy
  analysis ingestion path call that wrapper.
- A bounded Cookie-free Eastmoney news GET returned ten valid rows for
  `300750`. It is the same upstream as `stock_news_em`, so it must replace that
  wrapper rather than be presented as an independent additional source.
- The feasibility report approved public Eastmoney access only as a low-rate,
  personal-local fallback with exact endpoint, schema, timeout, attribution,
  and kill-switch boundaries. Login/session integration remains out of scope.
- The fundamentals audit found a separate correctness defect: provider-missing
  metrics are stored as zero, including PE for nearly every AkShare snapshot.
  Correcting 5,530 historical symbols requires a nullable migration and staged
  coverage recovery. It is deliberately separated from this availability fix
  so the existing 80 percent research gate is not silently invalidated mid-task.

## Requirements

### R1. Severe database-sparsity recovery

- Keep database-first behavior for daily bars, exact `(symbol, market)`
  identity, and all non-CN/non-stock/non-daily behavior.
- Compute a bounded severe-sparsity threshold from the requested weekday span:
  half of weekdays, rounded up, capped at the existing 35-row research-ready
  count and never below one.
- For an exact six-digit CN stock, return a coherent database cohort directly
  only when it meets that threshold and does not trigger the existing mixed-
  provenance recovery rule.
- When the cohort is below the threshold, retain it as a degraded fallback and
  run the existing requested -> AkShare Eastmoney -> AkShare Sina -> configured
  Tushare coordinator. Require the selected remote source to meet the same
  minimum row count; never stitch providers or adjustments.
- If every remote source is empty, invalid, or failed, return the prior non-
  empty database cohort with sanitized attempts and an explicit insufficient-
  coverage diagnostic. A GET must not write bars.

### R2. Cookie-free public news provider

- Add one site-specific `eastmoney_public` provider for the fixed HTTPS
  `search-api-web.eastmoney.com/search/jsonp` GET operation.
- Send only fixed public headers and query structure. Never send Cookie,
  Authorization, browser session state, caller-supplied URL/header values, or
  follow redirects.
- Apply the configured news timeout, a maximum response size, exact JSONP
  callback validation, expected media type, top-level success/result checks,
  bounded row count, row/schema validation, HTML-to-text normalization, exact
  article URL construction, symbol identity, finite timestamp handling, and
  stable sanitized errors. Do not retry within one refresh.
- Treat the existing `akshare_enabled` setting as the compatibility kill switch
  for this replacement public CN-news path. When it is false, make no Eastmoney
  request.

### R3. One real news chain

- Change exact CN detail refresh to stored -> configured executable providers
  -> `eastmoney_public` -> market-aware yfinance. Do not call
  `ak.stock_news_em` after the direct provider because both represent the same
  upstream.
- Keep first-persisted-success stopping, candidate normalization, URL/title
  dedupe, `NewsArticle`/`SentimentSignal` persistence, social non-citation, and
  the current no-data versus provider-error result semantics.
- Reuse the same public provider in the legacy `ingest_news(...,
  provider_name="akshare")` compatibility path so no production path retains
  the bundled Cookie/unbounded request.
- Expose `eastmoney_public` in refresh attempts and selected-provider metadata;
  keep publisher in the existing article `source` field. Persisted acquisition
  provenance is a separate schema task and must not be fabricated here.

### R4. Safety and compatibility

- Keep homepage news stored-read-only; do not add whole-market collection or
  page-load fan-out outside one exact instrument detail.
- Keep the frontend payload and one-shot/retry behavior compatible; do not show
  raw provider messages.
- Do not add login, Cookie replay, password/CAPTCHA handling, generic crawling,
  proxy rotation, raw HTML storage, trading behavior, or lower 95/90/80 gates.
- Preserve unrelated dirty files, normal 3000/8000 services, databases, Redis,
  workers, Beat, and the active five-day acceptance task.

## Acceptance Criteria

- [x] A sparse exact-CN database cohort triggers the existing remote
      coordinator and returns the first coherent source meeting the bounded
      threshold; sufficient, non-CN, mock, and short-range cohorts retain their
      prior behavior.
- [x] Remote failure preserves the sparse non-empty database cohort as degraded
      with `INSUFFICIENT_DATABASE_COVERAGE` and sanitized source attempts.
- [x] Public-news requests use the fixed HTTPS operation with no Cookie or
      Authorization, redirects off, configured timeout, response cap, strict
      JSONP/schema checks, and no retry.
- [x] Exact CN refresh reports `eastmoney_public`, persists normalized rows,
      stops on success, and falls through to yfinance on empty/error/timeout;
      neither refresh nor legacy ingestion calls `ak.stock_news_em`.
- [x] Homepage read-only behavior, frontend news payloads, AI stored-evidence
      boundaries, and all existing fallback contracts remain compatible.
- [x] Focused provider/service/API tests, relevant regression suites, Ruff,
      Trellis validation, redaction scans, and `git diff --check` pass without
      changing unrelated dirty files or the normal stack.

## Out Of Scope

- Fundamental metric nullability, historical placeholder cleanup, public
  Eastmoney finance/valuation ingestion, and full-universe fundamental backfill.
- Persisting news acquisition provider/retrieval time in a new database schema.
- Automatic homepage or full-universe news collection.
- Authenticated Eastmoney access or any account-private information.
