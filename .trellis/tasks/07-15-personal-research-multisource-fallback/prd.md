# Add automatic multi-source data and news fallback

## Goal

Make exact-instrument research useful without manual provider switching when a
stored or requested A-share data source is empty or unavailable. The workflow
must recover the best verified daily, intraday, and news evidence available,
while keeping unsupported data explicit and preserving the stored-evidence
boundary used by AI citations.

## Background

- The normal API process has not loaded the existing market-aware CN daily-bar
  fallback, even though current source code already supports database-first
  daily reads followed by yfinance, two AkShare sources, and Tushare.
- Four active CN symbols currently have mixed daily-bar provenance. The newest
  coherent database cohort contains only one or two rows, so it suppresses the
  existing remote fallback and makes the visible history incomplete.
- Intraday requests do not forward the resolved market. Most CN symbols can
  therefore miss yfinance ticker mapping, and AkShare has no wired minute-bar
  adapter in the current provider boundary.
- The normal database contains no stored news. Instrument detail reads only
  `GET /news/{symbol}`; configured credentialed search sources have no keys,
  while the existing yfinance and AkShare ingestion paths are not live search
  adapters.
- Frontend optional fetches currently collapse transport/provider failures and
  genuine empty results into the same unavailable presentation.

## Requirements

### R1. Daily-bar recovery

- Keep exact `market=CN`, six-digit stock, non-mock eligibility and the existing
  provider order.
- Keep one validated source and one adjustment for every returned series. Do
  not merge rows from different providers, sources, or adjustment modes.
- When mixed stored provenance leaves an incomplete newest cohort, attempt the
  existing coordinator for a complete single-source request window.
- If no remote source can provide sufficient coverage, retain the existing
  degraded database cohort rather than replacing usable rows with an empty
  payload.
- Preserve sanitized provenance and source-attempt metadata. A read request
  must not write daily bars.

### R2. Intraday fallback

- Forward the exact resolved market through Web, API, service, and provider
  construction.
- For eligible CN stocks, use historical cache first and then attempt the
  requested provider, AkShare Eastmoney minute data, and AkShare Sina minute
  data in fixed order, once per source and without retry.
- Preserve non-trading-day/future-date short circuits. HK, US, mock, and
  ambiguous identities must not enter the CN fallback.
- Normalize naive CN provider timestamps as Asia/Shanghai and expose exact
  effective source, fallback, freshness, and sanitized attempt state.
- Do not synthesize minute data from daily bars.

### R3. News fallback and persistence

- Keep `GET /news/{symbol}` read-only.
- Add one explicit refresh mutation for an exact `(symbol, market)` that first
  checks stored news, then tries configured executable search providers,
  AkShare for eligible CN symbols, and market-aware yfinance.
- Stop after the first source produces persistable news. Attempt every source
  at most once; do not retry timeouts, rate limits, provider errors, malformed
  data, or empty responses inside one refresh.
- Reuse current URL/title deduplication and `NewsArticle` plus
  `SentimentSignal` persistence. Social/public-opinion candidates remain
  non-citable and must not be stored as verified news.
- Return the final stored-news projection plus bounded diagnostic codes. Never
  return or persist credentials, cookies, authorization headers, raw provider
  bodies, or stack traces.
- Tushare news remains explicitly unimplemented until a verified news contract
  exists; mock is never a production fallback.

### R4. Personal-use UI behavior

- On exact instrument detail, stored news renders immediately. If it is empty,
  the browser visibly issues one refresh mutation per symbol, market, and local
  day, then updates only the news projection.
- Automatic failure is not retried. A visible retry command may perform one
  additional user-initiated attempt.
- Present recovering, no-data, provider-error, and unsupported states
  separately using localized diagnostic-code mappings. Do not render raw
  backend error messages.
- The homepage reads a bounded cross-symbol latest stored-news endpoint. It
  must not trigger provider searches for multiple instruments.
- Existing daily and intraday data continue rendering when degraded but
  non-empty.

### R5. Safety and scope boundaries

- Market depth, order book, trades, and large orders remain explicit
  unsupported/degraded states unless an independently verified provider
  capability exists. Never infer them from daily or minute data.
- Do not add generic crawling, browser-cookie extraction, authenticated
  scraping, proxy rotation, CAPTCHA bypass, paywall bypass, or raw HTML
  storage.
- A future public-web adapter must be site-specific, public/no-login,
  allowlisted, rate-limited, terms/robots aware, and disabled by default.
- Login-only material uses the existing manual visible-text/link import and
  reviewed citation workflow; browser credentials stay in the browser.
- Preserve no-investment-advice, no-order, no-portfolio, and no-automated-
  trading boundaries. Do not lower the 95/90/80 research gates.

## Acceptance Criteria

- [x] A mixed-provenance CN daily series either recovers one complete validated
      source or returns the prior non-empty database cohort as degraded; it
      never mixes source/adjustment rows or becomes empty because recovery
      failed.
- [x] Intraday requests carry exact market identity, use one verified source,
      fall back through the bounded CN order, preserve cache semantics, and
      distinguish all-empty from provider failure.
- [x] A detail page with stored news performs zero refresh mutations; an empty
      page performs exactly one automatic refresh and displays newly stored
      news without invoking the assistant or report generation.
- [x] News refresh is DB-first, stops after the first persisted success,
      deduplicates rows, preserves social/citation boundaries, and returns only
      sanitized diagnostics.
- [x] Homepage latest news is a bounded cross-symbol stored-news read and
      distinguishes failed loading from a genuine empty result.
- [x] Unsupported depth remains honest and contains no fabricated rows or
      crawler/cookie fallback.
- [x] Focused backend/API/frontend regressions, full relevant test suites,
      TypeScript, localization JSON, Ruff, production build, Trellis validation,
      and `git diff --check` pass.
- [x] The normal Web/API stack is reloaded only after validation; PostgreSQL,
      Redis, Worker, Beat, and the active five-day acceptance evidence remain
      preserved.

## Out of Scope

- Generic or authenticated web crawling, Cookie storage/replay, CAPTCHA or
  paywall bypass, proxy pools, and licensed full-text collection.
- New Tushare minute/news entitlements without a verified provider contract.
- Promoting AkShare market-depth candidate parsing to a trusted capability.
- Background whole-universe news crawling or automatic searches from the
  homepage.
- Changes to ranking, screening gates, trading behavior, or historical
  acceptance samples.
