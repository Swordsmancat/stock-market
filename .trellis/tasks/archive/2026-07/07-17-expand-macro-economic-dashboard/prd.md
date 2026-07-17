# Expand the macroeconomic dashboard

## Goal

Turn Macro Research into a scan-first personal macroeconomic dashboard that
shows the most decision-relevant indicators from the supplied reference image,
with truthful dates, sources, units, and compact trends, while preserving the
existing evidence-maintenance workflow.

## Background

- The current `/evidence` route leads with evidence operations and exposes only
  nine macro/valuation definitions.
- The existing `MarketIndicator` / `MarketIndicatorObservation` tables already
  support audited time-series observations without a migration.
- Runtime probes on 2026-07-17 verified current public AkShare-backed results
  for Eastmoney macro series, Jin10 SHIBOR, and Eastmoney China/US bond yields.
- The product is for personal research; the page should prioritize readable
  economic context over provider configuration and maintenance detail.

## Requirements

### R1. First-batch coverage

The dashboard must include the existing Buffett indicators and the following
verified first-batch series:

- rates: China LPR 1Y, China LPR 5Y, SHIBOR overnight, China 10Y government
  bond yield, US 10Y Treasury yield;
- economic fundamentals: China CPI YoY, PPI YoY, retail sales YoY,
  manufacturing PMI, GDP YoY;
- external economy: China exports YoY and imports YoY;
- money supply: China M2, M1, and M0 YoY;
- fiscal: national tax revenue YoY.

Each definition must have a stable code, category, region, unit, display order,
and localized display label. Existing codes and stored observations remain
compatible.

### R2. Audited refresh and partial failure

- Add an AkShare China-macro refresh path that normalizes verified provider
  frames into `MarketIndicatorObservation` rows.
- Store recent history, not only the newest value, so trends are locally
  reproducible.
- Every stored row must include source name/URL, provider function, retrieval
  time, methodology, and source field metadata.
- Provider or schema failure in one family must not delete or replace stored
  observations from other families. The response must report bounded,
  credential-free diagnostics and partial success.
- No fabricated, forward-filled, cross-period-stitched, or zero-substituted
  values are allowed.

### R3. Read-only dashboard contract

Expose a read-only dashboard payload grouped by stable category. Each item must
contain the latest observation, previous observation/change when available, a
bounded chronological sparkline, freshness state, and truthful missing-data
reason. Reading the dashboard must not call providers or mutate storage.

### R4. Personal-use interface

- `/evidence` must lead with the new macro dashboard, grouped as rates and
  liquidity, economic fundamentals, market valuation, external economy,
  money supply, and fiscal conditions.
- Cards show localized name, latest value/unit, comparable change, as-of date,
  source, freshness, and an accessible compact trend.
- The layout must fill wide screens, remain usable at 375px without horizontal
  overflow, and avoid color-only direction communication.
- A single explicit refresh action is available. Existing advanced evidence,
  source, import, disclosure, and notebook tools remain reachable inside a
  closed maintenance disclosure below the dashboard.
- Known raw codes and backend English no-data messages must not appear in the
  default Chinese view. Unknown codes retain a truthful fallback.

### R5. Scope and safety

- Do not add DR007, government-bond futures, index PE/dividend-yield series,
  detailed unemployment cohorts, commodity prices, or fiscal expenditure until
  their runtime schemas and source semantics are independently verified.
- Do not change AI citation eligibility, stock-selection rules, trading
  behavior, thresholds, or the existing five-day acceptance task.

## Acceptance Criteria

- [x] The API seeds all first-batch definitions and returns grouped stored
      history for all 23 configured dashboard items (the 14 verified additions
      plus the 9 existing US/valuation/money indicators).
- [x] Provider normalization tests cover valid frames, descending/ascending
      source order, missing values, malformed schemas, and partial family
      failure without fabricated observations.
- [x] API tests cover read-only dashboard payload and explicit AkShare refresh.
- [x] The Chinese and English pages render localized grouped cards, trends,
      dates, sources, missing states, and a closed maintenance disclosure.
- [x] The Chinese default view contains no known raw indicator codes or raw
      backend English no-data prose.
- [x] Desktop and 375px browser smoke checks have no horizontal overflow.
- [x] Full backend/frontend tests, type checks, Trellis validation, deployment,
      HTTP 200 health checks, commit, and push succeed.

## Out of Scope

- New database tables or migrations.
- Automatic provider calls on page GET.
- Background trading or investment advice.
- Scraping authenticated pages, cookie reuse, or bypassing access controls.
