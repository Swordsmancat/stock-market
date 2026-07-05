# Phase 2/3 Remaining Work Audit

## Phase 2 - Professional Feature Enhancement

| Feature | Current status | Remaining Work |
|---|---|---|
| K-line chart interactions | Complete for MVP | Professional workspace gaps remain: saved layouts, multi-chart grids, drawing tools, chart-linked alerts, and multi-timeframe synchronization. |
| Smart recommendations | Complete as research-signal MVP | Add historical backtesting, hit-rate/drawdown metrics, benchmark comparison, and stronger strategy explanation snapshots before presenting signals as professional-grade. |
| Hot sector rotation | Provider-backed MVP | Production provider verification is still needed for live sector ranking/fund-flow, breadth metrics, constituent contribution, and taxonomy governance. |
| Comparison analysis | Complete for MVP | Add deeper risk metrics, export refinements, and portfolio/watchlist-level comparison workflows. |

## Phase 3 - Advanced Features

| Feature | Current status | Remaining Work |
|---|---|---|
| Intraday chart | Provider-backed MVP | yfinance `1m` minute bars use an explicit provider method with `ok` / `no_data` / `degraded` semantics, previous-close reference, readiness checks, weekend no-data governance, and no daily-bar fabrication. Remaining work: production live-smoke success, cache/storage, holiday calendars, session windows, provider broadening, and streaming refresh. |
| Market depth data | Provider-boundary MVP | Explicit `fetch_market_depth` boundary, section-level status, AkShare fixture-tested candidate path, safe schema diagnostics, and verified-trade-only large-order derivation exist. Remaining work: reachable live provider smoke, schema-backed parser adaptation, entitlement/permission governance, recent-trade/fund-flow production validation, and order-flow analytics. |
| Technical indicators | Complete for MVP | MACD, RSI, KDJ, MA/BOLL-style indicator flows are covered. Remaining work is professional chart-workbench UX: indicator parameter persistence, presets, custom formulas, and multi-pane layout management. |
| AI assistant | MVP available | Natural-language assistant with citations/diagnostics/safety exists. Remaining work: multi-turn memory, document/report/news retrieval, richer citation UI, freshness diagnostics, and watchlist-level research monitoring. |

## Current Professional Gap Summary

- The platform now satisfies the core MVP for dashboard, charting, recommendations, comparison, intraday, depth-boundary, hot-sector contract, and AI assistant workflows.
- It does not yet match TradingView for chart workspace depth, Bloomberg/Koyfin/AlphaSense for research retrieval breadth, or broker Level-2 terminals for entitlement-backed order flow and low-latency streaming.
- The most important remaining production blockers are provider verification, market-calendar/session governance beyond weekend handling, persistent minute/depth storage, and professional research/backtesting workflows.

## Recommended Next Slices

1. Market data reliability: live-smoke provider verification, schema capture, provider permission governance, and cache/session handling.
2. AI research workflow: retrieval over reports/news/filings and stronger citation/freshness diagnostics.
3. Professional chart workspace: saved layouts, multi-timeframe sync, drawing tools, and chart-linked alerts.
4. Recommendation evaluation: backtesting, hit-rate, drawdown, benchmark comparison, and explainable signal history.
