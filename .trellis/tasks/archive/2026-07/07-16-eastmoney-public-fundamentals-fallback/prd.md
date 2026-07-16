# Add Eastmoney public fundamentals fallback

## Goal

Fill genuine A-share fundamental and company-context gaps in instrument detail
and AI analysis with a bounded, Cookie-free Eastmoney public fallback, without
adding account integration or fabricating missing financial values.

## Background

- Stored `FundamentalSnapshot` rows already feed detail, reports, and the market
  assistant and must remain authoritative.
- The current fallback uses static fixtures and existing ingestion adapters may
  convert missing values to zero. That is unsuitable for new live evidence.
- Read-only probes on 2026-07-16 verified Eastmoney's fixed financial summary
  and company survey GET endpoints without login or Cookie state.
- The financial report exposes revenue growth (`TOTALOPERATEREVETZ`), net margin
  (`XSJLL`), debt-to-assets (`ZCFZL`), currency, and report date. It does not
  expose a reliable PE value, which must remain null.

## Requirements

### R1. Strict public provider boundary

- Add an `eastmoney_public` provider for exact six-digit A-share symbols only.
- Use only fixed HTTPS GET endpoints for `RPT_F10_FINANCE_MAINFINADATA` and
  `PC_HSF10/CompanySurvey/PageAjax`; callers cannot supply URLs or headers.
- Disable redirects, send no Cookie/authorization, use an eight-second timeout,
  cap response bytes and row counts, and perform no retry.
- Validate HTTP status, known media types, response shape, symbol identity,
  report date, finite numeric values, and coherent report-period selection.
- Sanitize failures to stable codes plus exception type; never expose response
  bodies, query strings, URLs with parameters, headers, or exception messages.

### R2. Truthful normalized payload

- Map revenue growth, net margin, and debt-to-assets from percentage points to
  decimal ratios. Preserve unavailable PE as null.
- Add bounded company context: organization name, industry, business scope, and
  company profile. Missing profile fields remain null and do not invalidate
  otherwise valid financial metrics.
- Return provider/source attribution, upstream operation IDs, report as-of,
  retrieval time, status, diagnostics, and a deterministic fundamental citation.
- Do not stitch different report periods, copy prior values into newer periods,
  or turn missing values into zero.

### R3. Database-first, read-only fallback

- `get_fundamental_payload()` returns a stored database snapshot without any
  network call.
- When no stored row exists, use Eastmoney only for an exact six-digit symbol
  while the existing public A-share source gate is enabled.
- Cache successful and explicit no-data normalized payloads in Redis for 30
  minutes. Cache failures never block a truthful response.
- GET/detail/AI/report reads never write a `FundamentalSnapshot` or other row.
- Eastmoney empty/failure returns explicit no-data/unavailable for exact A-share
  symbols rather than falling through to a static mock fixture.
- Existing US/HK and explicit ingestion behavior remains unchanged.

### R4. Detail and AI integration

- Extend the existing fundamentals response additively; no route change.
- Instrument detail renders company context only when present and continues to
  render unavailable labels for null metrics.
- The market assistant includes bounded industry/business/profile context in
  the same fundamental citation and retains citation validation and safety rules.
- No account login, Cookie import, CAPTCHA, watchlist/portfolio access, bulk
  crawl, trading action, or change to 95/90/80 research thresholds.

## Acceptance Criteria

- [x] Provider tests cover exact request parameters, no credentials/redirects,
      response bounds, schema/identity/date/numeric validation, percentage
      normalization, profile bounding, empty results, and sanitized failures.
- [x] Service tests prove database success makes zero network calls, eligible
      A-share gaps use one normalized Eastmoney result, Redis cache prevents a
      second provider call, and cache failure remains non-blocking.
- [x] Exact A-share empty/failure stays truthful and writes zero database rows;
      non-A-share symbols preserve existing behavior.
- [x] API/detail tests cover additive company context and null PE presentation.
- [x] Assistant tests prove the fundamental citation contains normalized metrics
      and bounded company context without unknown citations or raw provider data.
- [x] Focused/full Python and web tests, Ruff, mypy/TypeScript, Trellis validation,
      redaction checks, and live read-only acceptance pass.

## Out Of Scope

- Eastmoney login/session/Cookie handling or account-only data.
- Direct quote, K-line, fund-flow, announcement, or news changes.
- Database migration, persistent raw Eastmoney payloads, bulk refresh/backfill,
  scheduler changes, or replacing CNINFO/official evidence.
