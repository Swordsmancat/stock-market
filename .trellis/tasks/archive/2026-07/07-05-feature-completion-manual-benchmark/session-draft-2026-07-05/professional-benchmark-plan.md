# Professional Benchmark and Trellis Execution Plan

## Benchmark Baseline

The current product is evaluated against common capabilities from professional and semi-professional financial platforms:

- TradingView-style charting and technical-analysis workspace.
- Yahoo Finance-style quote pages, watchlists, fundamentals, news, and comparison views.
- Bloomberg-style terminal workflows for data provenance, depth, analytics, and research context.
- Eastmoney / Tonghuashun-style China-market dashboards, sector flow, market breadth, and capital-flow views.
- Futu / Moomoo-style watchlists, quote detail pages, alerts, news streams, and chart workspaces.

This benchmark does not require exact product parity. It identifies which professional expectations are already covered, which are acceptable MVP gaps, and which gaps should become Trellis execution tasks.

## Capability Comparison

| Benchmark Dimension | Professional Expectation | Current Implementation | Status | Trellis Mapping |
|---|---|---|---|---|
| Landing/dashboard discoverability | Localized dashboard with market overview, watchlist, signals, sectors, and quick navigation. | Dashboard entry and localized pages exist; major feature cards are discoverable. | Meets MVP | Continue UX polish outside this audit. |
| Quote and instrument detail | Latest quote, daily bars, indicators, news/research context, fundamentals, and related actions. | Instrument page integrates quote, historical bars, indicators, intraday/depth cards, AI assistant, and related surfaces. | Meets MVP / partial professional | Future fundamentals/corporate-actions task if prioritized. |
| Charting workspace | Multi-timeframe chart, indicators, layouts, drawings, comparison, alerts, and saved presets. | Daily chart and indicators exist; local workspace save/restore/reset and research annotation were added. | Partial | `07-05-professional-chart-workspace-enhancements` completed first slice; future tasks for multi-pane, drawings, synced presets, and alerts. |
| Intraday data reliability | Verified minute data, session calendars, freshness, persistent cache, and provider failure semantics. | yfinance minute-bar MVP and freshness/session metadata exist; persistent closed-session cache governance is ongoing. | Partial | `07-05-persistent-intraday-cache-calendar-governance`, `07-04-real-intraday-minute-data-pipeline`. |
| Market depth / Level-2 | Verified order book, recent trades, large orders, fund flow, permissions, and schema monitoring. | Explicit provider boundary exists; unsupported data remains degraded-safe; AkShare path is fixture-tested. | Partial / provider-dependent | `07-04-real-market-depth-provider-pipeline`. |
| Sector flow and breadth | Sector ranking, fund flow, constituent breadth, leaders/laggards, rotation history, and provider taxonomy. | Provider capability metadata, breadth, contribution, taxonomy, and unavailable rotation-history semantics were added. | Partial but improved | `07-05-hot-sector-production-breadth-rotation-history` completed first slice; future persistence/provider verification task. |
| Recommendation analytics | Signal definitions, history, hit rate, forward returns, drawdown, benchmark comparison, and validation diagnostics. | Service-level deterministic signal evaluation was added for all current signal types. | Partial but improved | `07-05-recommendation-backtesting-signal-evaluation` completed first slice; future API/UI/persistence/walk-forward tasks. |
| AI research assistant | Cited evidence, reliable source metadata, filings/news/reports, transcript coverage, retrieval quality, and hallucination guardrails. | Evidence/citation MVP exists for local bars, indicators, fundamentals, news, and reports with citation diagnostics. | Partial | `07-05-ai-research-retrieval-citations` completed first slice; future filings/transcripts/vector retrieval tasks. |
| Watchlist, alerts, portfolio, reports | Persistent user surfaces, notifications, portfolio analytics, and generated reports. | API surfaces and dashboard cards exist. | Meets MVP / partial professional | Future task for realtime monitoring and attribution if prioritized. |
| Degraded-safe data contract | No fake live data, explicit unavailable states, provider metadata, freshness, and diagnostics. | Degraded-safe contract is documented and applied to intraday, depth, hot sectors, and recommendations. | Meets MVP / ongoing | Continue through provider-specific tasks. |

## Prioritized Improvement Plan

### P0 - Data correctness and provider trust

Professional finance products first need reliable provenance. These tasks should remain ahead of visual polish.

1. **Persistent intraday cache and exchange-calendar governance**
   - Trellis task: `07-05-persistent-intraday-cache-calendar-governance`.
   - Goal: cache verified closed-session minute bars, prevent future/weekend/holiday provider misuse, and expose clear freshness/session metadata.
   - Acceptance focus: no fabricated minute bars; deterministic cache tests; typed `freshness` and `session` metadata.

2. **Real intraday minute provider pipeline**
   - Trellis task: `07-04-real-intraday-minute-data-pipeline`.
   - Goal: improve verified provider minute data beyond the first yfinance MVP and document provider limits.
   - Acceptance focus: provider smoke/readiness, no-data semantics, and page-level resilience.

3. **Real market depth provider pipeline**
   - Trellis task: `07-04-real-market-depth-provider-pipeline`.
   - Goal: move depth/recent-trade/fund-flow sections from degraded boundary to verified provider-backed data where possible.
   - Acceptance focus: provider permission/schema validation, no secret leakage, and section-level degraded states.

### P1 - Research quality and China-market professional workflows

4. **AI research retrieval and citation expansion**
   - Trellis task: `07-05-ai-research-retrieval-citations` plus future children.
   - Current first slice: local evidence/citation MVP.
   - Next improvement: filings, transcripts, exchange announcements, provider research feeds, and source-quality scoring.

5. **Hot-sector provider verification and rotation snapshots**
   - Trellis task: follow-up to `07-05-hot-sector-production-breadth-rotation-history`.
   - Current first slice: capability matrix, breadth, contribution, taxonomy, and unavailable history semantics.
   - Next improvement: provider-verified breadth, persistent rotation-history snapshots, and trend/turnover views.

### P2 - Professional workspace and analytics depth

6. **Chart workspace parity upgrades**
   - Trellis task: follow-up to `07-05-professional-chart-workspace-enhancements`.
   - Current first slice: browser-local preset and research annotation.
   - Next improvement: multi-pane layout, indicator parameters, drawing tools, comparison overlays, and optional account sync.

7. **Recommendation evaluation productization**
   - Trellis task: follow-up to `07-05-recommendation-backtesting-signal-evaluation`.
   - Current first slice: deterministic service-level evaluation.
   - Next improvement: public API/UI display, persistent signal history, transaction costs/slippage, portfolio simulation, benchmark universe controls, and walk-forward validation.

8. **Watchlist / portfolio professionalization**
   - Trellis task: create only after provider reliability work stabilizes.
   - Goal: realtime watchlist monitoring, alert delivery channels, portfolio attribution, and risk summaries.

## Current Requirement Fit

The current implementation meets the user's near-term requirement for an MVP market-analysis website:

- Users can enter the localized dashboard, inspect market and instrument pages, view charts and indicators, see degraded-safe intraday/depth/sector states, use AI research assistance, and read documentation about limitations.
- The system now has first-slice professionalization for chart workspace persistence, hot-sector metadata, and recommendation signal evaluation.
- The manuals document that research features are not investment advice and that unavailable provider data must not be treated as live market truth.

The current implementation does not yet meet professional-terminal parity:

- It lacks fully verified Level-2 depth, robust intraday persistence across markets, full exchange calendars, real sector rotation history, advanced chart scripting/drawing, persistent signal history, and institutional-grade research retrieval.
- These gaps are broad and provider-dependent, so they should continue through the Trellis tasks above rather than through a single audit patch.

## Execution Decision

The broad scope justified Trellis usage. The parent audit task should remain the coordination record, while implementation continues in child or cross-linked tasks. Completed first slices should be considered accepted MVP improvements; remaining professional parity work should be prioritized by provider trust first, research depth second, and workspace polish third.
