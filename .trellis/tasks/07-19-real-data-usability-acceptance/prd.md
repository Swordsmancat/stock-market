# Accept real-data usability and missing states

## Goal

Verify that Market Movers, Stock Comparison, Unified K-line, and Topic
Research are useful with the current production-local database, then make the
smallest UI changes needed to explain unavailable data accurately.

## Background

The four modules were implemented as database-first read surfaces. Initial
read-only probes on 2026-07-19 found:

- Market Movers is ready through 2026-07-17 with 5,518 comparable stocks.
- Stock Comparison is intentionally empty before selection; `000001` and
  `600519` produce 64 shared dates through 2026-07-17.
- Stored stock K-lines are ready, but the catalog contains zero ETFs and zero
  indexes. This is an ingestion/catalog coverage gap, not a page-load failure.
- All four topic projections have news and industry-ranking evidence. Company
  metadata is absent for several topics and must remain an explicit partial
  coverage state.

## Requirements

- Validate all four public GET APIs and Chinese pages against the running
  local stack without initiating provider, crawler, ingestion, backfill, AI,
  watchlist, portfolio, order, or trading mutations.
- Record data date, stored counts, provenance, selection prerequisites, and
  section-level coverage in a task-owned acceptance artifact.
- Distinguish at least these user-visible states where they occur:
  selection required, unsupported or uncollected asset catalog, selected
  identity not found, stored identity without a valid series, partial topic
  evidence, and actual load failure.
- Do not label a valid selection prerequisite as missing data.
- Do not fabricate ETF/index rows, topic companies, prices, or news and do not
  add a live fallback to any read page.
- Reuse existing localized empty/error components and messages. Add only the
  minimum contextual copy needed to identify the cause and next relevant
  location, such as Storage or Crawler Monitor.
- Preserve compact personal-use navigation and the five-item mobile set.
- Leave the active five-day research acceptance task and its evidence files
  untouched.

## Acceptance Criteria

- [x] A sanitized acceptance artifact records the actual result of every
      module and separates product behavior from storage coverage gaps.
- [x] Market Movers and a two-stock comparison render current stored data.
- [x] A selected stored stock renders a nonblank K-line, while ETF/index empty
      catalogs truthfully identify missing stored coverage.
- [x] All four topic views preserve available sections and describe empty
      company sections without hiding news or industry evidence.
- [x] Empty, precondition, no-data, and load-failure states remain distinct in
      both Chinese and English catalogs.
- [x] Focused tests, full Web tests, TypeScript, locale JSON parsing, Trellis
      validation, and scoped `git diff --check` pass.

## Out of Scope

- Adding or running a new provider, crawler, backfill, or ingestion schedule.
- Filling ETF/index or topic-company storage during this task.
- New dashboards, navigation destinations, AI conclusions, or trading flows.
- Changing the 95/90/80 research thresholds or five-day acceptance samples.
