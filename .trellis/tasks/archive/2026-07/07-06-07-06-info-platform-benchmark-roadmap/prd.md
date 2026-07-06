# Information Platform Benchmark and Next Roadmap

## Goal

Compare the implemented personal investment information cockpit against mature information and research platforms, complete the user manual positioning, and produce a Trellis follow-up execution plan focused on source aggregation, macro indicators, hard-to-find data, and AI summaries.

## Background

The parent task has completed the first implementation wave:

- Macro/valuation indicator definitions and no-data-safe dashboard brief.
- Information source readiness registry with collection links and citation boundaries.
- Audited macro seed import.
- Citation-aware dashboard AI narrative with deterministic fallback.
- Source-to-seed templates for FRED/PBOC/Buffett/user seed files.

The user clarified that the product is for personal information aggregation and AI research summaries, not professional trading-terminal competition.

## Requirements

### R1. Benchmark Against Information Platforms

- Compare against information and research products, not broker terminals:
  - Koyfin: macro dashboards, market dashboards, economic calendars, watchlists.
  - MacroMicro: global macro charts, daily macro snapshots, economic-cycle interpretation.
  - TradingView/Yahoo-style public investor tools: watchlists, charts, news flow, screeners, calendars.
  - AlphaSense: AI search, document/research monitoring, auditable summaries and alerts.
  - FRED, World Bank, SEC EDGAR, Trading Economics: official/public or API-style source candidates.
- Call out what the current implementation already satisfies and where it is intentionally smaller.

### R2. Current Capability Fit

- Evaluate whether the implemented functions satisfy the revised personal-use need:
  - information aggregation.
  - macro/valuation collection.
  - hard-to-find source preparation.
  - AI summary/recommendation positioning.
  - transparent source and citation boundaries.
- Avoid judging the product by Level-2, order flow, broker execution, or low-latency terminal parity.

### R3. User Manual Completion

- Update `docs/manual/user-guide.md` with a concise benchmark and roadmap section that reflects the current implemented state.
- Keep the manual honest:
  - no investment advice.
  - no automatic trading.
  - no automatic scraping/ingestion unless a future source adapter is explicitly implemented.
  - source links and templates are not AI citations until audited local evidence exists.

### R4. Trellis Follow-Up Plan

- Produce a follow-up plan that can become Trellis tasks.
- Prioritize personal value:
  - source pipeline and adapters.
  - macro calendar / release tracking.
  - daily/weekly AI digest workflow.
  - watchlist-source monitoring.
  - document/source notebook and saved AI follow-ups.
- Mark terminal-grade features as optional later.

## Acceptance Criteria

- [ ] A research note under this task compares current capability with information/research platforms and source APIs.
- [ ] `docs/manual/user-guide.md` contains a current-state benchmark and roadmap section aligned with the personal research cockpit direction.
- [ ] The plan lists P0/P1/P2 follow-up Trellis tasks and explicitly says which features should not be pursued now.
- [ ] No runtime behavior changes are introduced.
- [ ] Validation passes for documentation diff and existing full backend/frontend checks remain attributable to the earlier verified state or are rerun if docs are the only change.

## Notes

- This is a planning/docs slice. It may use external research links, but should not add runtime network calls.
- Keep code changes out of scope unless docs reveal a broken test or a false product claim.
