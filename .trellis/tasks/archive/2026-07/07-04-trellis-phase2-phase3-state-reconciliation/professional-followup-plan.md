# Professional Platform Follow-up Execution Plan

## Current Status Summary

The current implementation satisfies the core MVP for dashboard navigation, charting, recommendations, comparison, hot sectors, intraday minute payloads, market-depth provider boundaries, and AI assistant workflows. It should not yet be presented as equivalent to a professional market terminal.

## Benchmark Gaps

| Benchmark | Current coverage | Remaining gap |
|---|---|---|
| TradingView | Interactive charting and common indicators exist | Saved layouts, multi-chart workspaces, drawing tools, custom formulas, chart-linked alerts, and multi-timeframe synchronization remain. |
| Bloomberg / Koyfin | Fundamentals, reports, news payloads, and assistant MVP exist | Research retrieval, multi-document citations, filings/transcripts, notebook workflows, freshness diagnostics, and watchlist-level narrative monitoring remain. |
| AlphaSense | Assistant has answer/citation/diagnostic boundaries | Broad document search, entity/topic retrieval, transcript and filing synthesis, and persistent research sessions remain. |
| Broker Level-2 terminal | Explicit depth provider boundary and partial-section semantics exist | Production-verified Level-2, reachable live provider smoke, entitlement governance, recent trades, order-flow analytics, heatmaps, and low-latency streaming remain. |
| CN retail terminal | Hot-sector and AkShare candidate contracts exist | Production sector breadth, advancers/decliners, constituent contribution, Dragon-Tiger list / announcement integration, local calendars, quota/permission governance, and verified A-share provider coverage remain. |

## P0 Execution Plan

1. Market-data reliability and provider verification.
   - Keep AkShare depth and yfinance intraday live smoke opt-in and non-writing.
   - Capture safe diagnostics only; do not fabricate missing Level-2 or minute rows.
   - Add fixture-backed parser updates only after a reachable live environment exposes schema samples.
2. Intraday session governance.
   - Weekend `no_data` is implemented.
   - Next slices should add exchange calendars, holiday handling, session windows, cache/storage, and stale/freshness metadata.
3. Depth provider maturity.
   - Safe schema diagnostics are implemented.
   - Next slices should validate a reachable provider, normalize recent trades and fund-flow where permitted, and keep large orders derived only from verified trades.

## P1 Execution Plan

1. AI research retrieval.
   - Add retrieval over reports/news/filings or transcripts.
   - Preserve safe answer boundaries and visible citation/freshness diagnostics.
2. Hot-sector production breadth.
   - Add verified provider coverage for sector ranking/fund-flow.
   - Add breadth metrics and constituent contribution snapshots.

## P2 Execution Plan

1. Professional chart workspace.
   - Saved layouts, drawing tools, linked multi-timeframe panels, and chart-linked alerts.
2. Recommendation evaluation.
   - Backtesting, hit-rate, drawdown, benchmark comparison, and explainable signal history.

## Trellis Mapping

- Continue provider-verification work in `07-04-real-market-depth-provider-pipeline` and `07-04-real-intraday-minute-data-pipeline`.
- Create focused future child tasks only when implementation can be independently validated:
  - `market-data-calendar-cache-governance`,
  - `ai-research-retrieval-workflow`,
  - `professional-chart-workspace`,
  - `recommendation-backtesting-evaluation`.

## Current Decision

Do not archive the Phase 2/3 parent as fully complete. The MVP status is substantially improved, but professional parity requires the follow-up slices above.
