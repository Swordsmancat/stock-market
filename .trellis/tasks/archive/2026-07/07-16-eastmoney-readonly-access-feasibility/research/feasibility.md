# Eastmoney read-only access feasibility

## Decision

- Public-data integration: **conditional GO only as a bounded, low-frequency,
  read-only fallback for personal local research**. Prefer the existing AkShare
  adapters and official sources. A direct Eastmoney adapter should be added
  only for a verified gap, use exact endpoint allowlists and strict schema
  validation, and remain independently disableable.
- Authenticated session integration: **NO-GO for the current product scope**.
  No required research dataset was found that needs an Eastmoney login. The
  incremental account-only capabilities are primarily private watchlists,
  portfolios, and account messages, not missing market evidence.
- Automated login, password capture, CAPTCHA handling, browser-profile Cookie
  extraction, authenticated HTML crawling, and account write actions: **NO-GO**.

This is a technical feasibility result, not a grant of permission to collect,
store, or redistribute Eastmoney content. Public reachability does not remove
copyright, exchange-data, contract, or attribution obligations.

## Probe boundary

The public probes ran on 2026-07-16 with `UseCookies=false`, redirects disabled,
and no Cookie, authorization header, login, browser state, POST request, or
persistent write. The probe recorded only HTTP/result shape and bounded schema
metadata. It used `600519` / `600519.SH` as a representative A-share identity.

The results are a point-in-time reachability sample. These endpoints are
undocumented web internals and do not carry a version or availability promise.

## Current repository coverage

| Category | Existing path | Current behavior | Incremental value from direct Eastmoney |
| --- | --- | --- | --- |
| A-share daily bars | `packages/providers/akshare_provider.py:260`; coordinator in `packages/services/market_data.py:648` | Database/requested source, AkShare Eastmoney, AkShare Sina, then configured Tushare; source validation and provenance are retained | None demonstrated |
| A-share minute bars | `packages/providers/akshare_provider.py:335`; fallback construction in `packages/services/market_data.py:747` | Persistent cache, requested source, AkShare Eastmoney, then AkShare Sina | None demonstrated |
| Market depth | `packages/providers/akshare_provider.py:389` | AkShare `stock_bid_ask_em`; candidate research context, not production Level-2 | None demonstrated |
| Stock fund flow | `packages/services/market_daily_data.py:293` | AkShare `stock_individual_fund_flow_rank`, Eastmoney-backed | Low: a direct endpoint could only be a last fallback |
| Sector fund flow | `packages/services/hot_sectors.py:227` | AkShare `stock_sector_fund_flow_rank`, Eastmoney-backed | None demonstrated; public probe was unstable |
| Limit-up pool | `packages/services/market_daily_data.py:450` | AkShare `stock_zt_pool_em`; missing reason fields remain explicit | None demonstrated |
| Dragon Tiger List | `packages/services/market_daily_data.py:637` | AkShare `stock_lhb_detail_em` | None demonstrated |
| Block trades | `packages/services/market_daily_data.py:825` | AkShare `stock_dzjy_mrmx` | None demonstrated |
| News | Legacy ingestion at `packages/services/news.py:399`; active fallback chain at `packages/services/news_search.py:621` | Stored rows, configured search sources, AkShare `stock_news_em`, then yfinance | Limited: search may find extra links, but the endpoint is brittle and licensing-sensitive |
| Fundamentals | `packages/services/fundamentals.py:221` | AkShare `stock_financial_analysis_indicator`; persisted through task/backfill paths | Limited: public finance/company-profile endpoints could fill selected gaps |
| Instrument universe | `packages/providers/akshare_provider.py:413` | AkShare `stock_info_a_code_name` | None demonstrated |
| Dividends | `packages/providers/akshare_provider.py:419` | AkShare `stock_fhps_em` | None demonstrated |
| Official disclosures | `packages/providers/cninfo_disclosure_provider.py:149` | CNINFO is retained as the official evidence source | Eastmoney should not replace the official source |

No repository code stores an Eastmoney account, Cookie, or logged-in session.
Existing Eastmoney-backed rows often identify only the adapter as `akshare`;
future work should distinguish `provider` from `upstream_source` consistently.

## Public GET evidence

| Category | Public host/path | Observation | Classification | Recommendation |
| --- | --- | --- | --- | --- |
| Quote | `push2.eastmoney.com/api/qt/stock/get` | Both bounded clients were disconnected before an HTTP response | Public but brittle; overlaps current coverage | Do not add as a primary or duplicate source |
| Daily K-line | `push2his.eastmoney.com/api/qt/stock/kline/get` | Both bounded clients were disconnected before an HTTP response | Public but brittle; overlaps current coverage | Keep the existing resilient AkShare chain |
| Intraday trend | `push2his.eastmoney.com/api/qt/stock/trends2/get` | HTTP 200 JSON; `data.trends` was present | Public, undocumented, schema-coded with `fXX` fields | Existing minute path is sufficient |
| Stock fund flow | `push2his.eastmoney.com/api/qt/stock/fflow/kline/get` | HTTP 200 JSON; `data.klines` was present | Public, undocumented, limited incremental value | Candidate last fallback only after a repeated product gap |
| Sector fund flow | `push2.eastmoney.com/api/qt/clist/get` | Both bounded clients were disconnected before an HTTP response | Public but brittle | Does not improve current reliability |
| News search | `search-api-web.eastmoney.com/search/jsonp` | Missing callback returned HTTP 400; a public callback returned HTTP 200 JSONP with results | Public but highly brittle and licensing-sensitive | Link discovery only; validate every row and retain publication/retrieval time |
| Announcements | `np-anotice-stock.eastmoney.com/api/security/ann` | HTTP 200; JSON body reported as `text/plain` | Public but weakly contracted | Discovery fallback only; cite CNINFO/exchange/issuer as the authoritative evidence |
| Financial indicators | `datacenter.eastmoney.com/securities/api/data/v1/get` | HTTP 200; `success=true` and finance rows in a `text/plain` response | Public but undocumented | Candidate fallback for selected normalized fields |
| Company profile | `emweb.securities.eastmoney.com/PC_HSF10/CompanySurvey/PageAjax` | HTTP 200 JSON with company-profile sections | Public but undocumented | Candidate fallback only when the field has a defined source and as-of contract |

The quote, daily-bar, and sector-flow failures occurred while related public
Eastmoney hosts succeeded in the same probe window. This points to endpoint-
specific blocking or instability, not a login requirement. Adding a Cookie
would not establish reliability and could increase account risk.

## Reliability and evidence risks

- The web APIs use opaque field identifiers, JSONP, mismatched content types,
  and no version contract. A response can be HTTP 200 and still be unusable.
- Direct Eastmoney market-data paths currently offer less resilience than the
  repository's explicit multi-source coordinators.
- Market-daily and sector services have weaker timeout, pacing, cache, and
  wrapper-schema tests than the daily-bar coordinator. A new direct adapter
  must not copy those omissions.
- Fundamentals currently suppress broad exceptions and can project missing
  values as zero. Any new source must preserve missingness and reject partial
  or contradictory rows instead of expanding this behavior.
- An aggregator should not replace an official source for announcements,
  exchange facts, or issuer documents. Discovery metadata and authoritative
  evidence must remain distinct.
- `provider=akshare` is not enough provenance when AkShare wraps Eastmoney,
  Sina, or CNINFO. Store and expose a normalized upstream source separately.

## Licensing and attribution

The Eastmoney site links to its public legal statement at
`https://about.eastmoney.com/home/legal` and privacy statement at
`https://about.eastmoney.com/home/conceal`. The legal statement says that site
materials are protected and restricts copying, modification, republication,
distribution, and dissemination without the relevant written permission. It
also specifically states that exchange market information may not be copied or
disseminated without the relevant exchange's written consent, and disclaims
accuracy, completeness, timeliness, and reliability.

Therefore:

- public access is not evidence of a redistribution or bulk-collection right;
- direct use should remain local, personal, bounded, attributed, and minimally
  cached unless permission and data terms are reviewed;
- long-term bulk storage, republishing, or an externally exposed feed remains
  NO-GO without explicit authorization;
- every accepted row needs upstream source, source URL or operation identity,
  source publication/as-of time when available, retrieval time, and diagnostics.

## Public adapter guardrails

If a later task demonstrates a repeated gap and adds `eastmoney_public`, it
must have all of the following:

1. Fixed HTTPS host/path/operation allowlists and GET-only requests; no caller-
   supplied URL or headers, no redirects, and no private-network destinations.
2. Bounded connect/read timeout, response-size limit, single low-concurrency
   lane, low request rate, short cache, circuit breaker, and provider kill
   switch. Retries must be rare, bounded, and only for classified transient
   failures.
3. Endpoint-specific schema validation, explicit field mappings, identity/date
   checks, finite numeric checks, and fail-closed handling of HTML/login pages,
   JSONP drift, content-type mismatch, and contradictory counts.
4. One coherent source per result. Never stitch partial rows across providers
   and never fabricate absent fields or timestamps.
5. Separate `provider=eastmoney_public` from `upstream_source`; preserve source
   attribution, retrieval time, fallback attempts, and sanitized error codes.
6. No raw response bodies, query strings, exception messages, keys, Cookie,
   authorization values, or credential-bearing URLs in logs, TaskRuns, API
   payloads, test snapshots, or evidence artifacts.
7. Focused contract tests plus a bounded live acceptance before enabling the
   adapter by default.

## Authenticated-session assessment

The current settings boundary is not suitable for bearer session credentials:

- `packages/services/platform_settings.py:23,175-227,294-350` reads and writes
  key-like settings in `data/platform_settings.json`;
- `apps/api/routers/settings.py:132-140` exposes settings operations without a
  local session-vault boundary;
- `docker-compose.yml:27-35` publishes the API on port 8000 and starts it on
  `0.0.0.0`;
- `pyproject.toml:5-18` has no OS keyring or encryption dependency.

A session Cookie is a bearer credential even if this application sends only
GET requests. Leakage could allow another tool to perform account writes. It
must never be stored in the existing settings JSON, environment dumps, command
arguments, frontend storage, database, Redis, TaskRun, or worker payloads.

If a future, separately approved task proves a specific account-only need, the
minimum acceptable design is:

- explicit manual import through local stdin/getpass; never read an existing
  browser profile, capture a password, automate login, or solve a CAPTCHA;
- storage in Windows Credential Manager or another OS-backed secret vault,
  with explicit revoke and expiry state;
- API-process-only, short-lived access to the secret; no worker/beat forwarding
  and no persistent Cookie jar;
- a separate default-off `eastmoney_session` provider and kill switch;
- hard-coded GET operations with exact HTTPS allowlists, redirects disabled,
  proxy inheritance disabled, strict response limits and schemas, low rate and
  concurrency, and no automatic retry;
- 3xx, 401, 403, login HTML, or session challenges classified as `expired`,
  followed by immediate circuit opening and no automated reauthentication;
- diagnostics limited to safe operation ID, status class, elapsed bucket,
  cache state, and enumerated error code.

This conditional design is not approved for implementation by this report.

## Final go/no-go matrix

| Decision | Result | Reason |
| --- | --- | --- |
| Continue current AkShare/Eastmoney public paths | GO | They already cover the core product and participate in bounded fallbacks |
| Add direct Eastmoney quote/K-line/intraday duplicate paths now | NO-GO | No material increment and observed endpoint instability |
| Research a direct public news/fund-flow/fundamental fallback after repeated gaps | CONDITIONAL GO | Some incremental discovery value, but only with strict contracts and rights review |
| Replace CNINFO/exchange/issuer evidence with Eastmoney | NO-GO | Aggregated discovery is not authoritative evidence |
| Import an Eastmoney logged-in session now | NO-GO | No proven account-only research requirement and no safe credential boundary |
| Capture passwords, automate CAPTCHA, or extract browser Cookies | NO-GO | Disproportionate security, consent, maintenance, and access-control risk |

The smallest appropriate next product step is to improve provenance, timeout,
schema, and fallback behavior around the existing public providers. Revisit an
authenticated session only when the user names one indispensable account-only
field that public or official sources cannot provide.
