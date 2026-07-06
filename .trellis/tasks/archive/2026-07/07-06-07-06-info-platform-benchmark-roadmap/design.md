# Design: Information Platform Benchmark and Next Roadmap

## Boundary

This task is a benchmark, documentation, and roadmap slice. It does not change application code, database schemas, source adapters, or AI generation behavior.

## Current Capability Frame

The implemented product now has the right shape for a personal research cockpit:

- Dashboard aggregates market overview, watchlist context, reports, recommendations, news, macro indicators, source readiness, and diagnostics.
- Macro/valuation layer includes Buffett Indicator and key rates/inflation/liquidity definitions with no-data-safe behavior.
- Audited seed import and source-to-seed templates help the user prepare hard-to-find macro/valuation observations.
- Dashboard AI brief can summarize existing evidence with citation validation and deterministic fallback.
- Source readiness separates collection guidance from citable evidence.

## Benchmark Dimensions

Use four benchmark dimensions instead of terminal parity:

1. Source breadth and auditability:
   - Compare with FRED, World Bank, SEC EDGAR, Trading Economics.
   - Output should identify adapter/import candidates and metadata requirements.
2. Macro dashboard organization:
   - Compare with Koyfin and MacroMicro.
   - Output should identify grouping, calendar, cross-indicator charting, and daily snapshot gaps.
3. Personal workflow:
   - Compare with TradingView-style watchlist/news/calendar workflows.
   - Output should identify daily/weekly digest and monitoring gaps.
4. AI research synthesis:
   - Compare with AlphaSense-style search, monitoring, and auditable AI summaries.
   - Output should identify document corpus, saved briefs, notebooks, and citation-density gaps.

## Manual Update Shape

Add or revise the professional comparison / roadmap section in `docs/manual/user-guide.md`:

- State that current implementation meets the MVP requirement for personal aggregation plus AI-safe summaries.
- Separate implemented, partially implemented, and next-step capabilities.
- Keep source links, seed templates, and missing-source statuses outside the citation boundary.
- Present next tasks in P0/P1/P2 order.

## Follow-Up Plan Shape

The plan should produce Trellis-ready slices:

- P0: official macro adapter MVP and release calendar readiness.
- P1: daily/weekly digest workflow with persisted brief history.
- P1: watchlist event/source monitor.
- P1: research source notebook / saved AI follow-ups.
- P2: document ingestion for SEC filings/transcripts where legal/source boundaries are clear.
- Later optional: terminal-style workstations, Level-2/order-flow, broker integration.

## Validation

Because this is a docs/planning task:

- Verify changed docs are readable and do not conflict with current implementation.
- Run `git diff --check`.
- Reuse prior full validation results if no runtime code changes occur; rerun focused tests only if docs/test files change in a way that requires it.
