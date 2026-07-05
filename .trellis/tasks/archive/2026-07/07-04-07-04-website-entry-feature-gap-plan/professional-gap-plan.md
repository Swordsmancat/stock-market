# Professional Feature Gap and Optimization Plan

## Entry Stability Result

`http://localhost:3000/zh` has been checked in the browser and rendered the localized dashboard successfully. The observed page contained the top navigation, localized sidebar, dashboard title, market overview content, watchlist/action links, comparison controls, and the Next.js page title `Stock Analysis Platform`.

The blocking React Server Component boundary issue was caused by passing a function from the homepage Server Component into the `SmartRecommendations` Client Component. The fix removes that function prop and lets the client component keep using its default serialized href construction.

The reported `next-themes` script warning did not block the observed `/zh` render. It should remain a follow-up only if it reappears as a blocking overlay, hard hydration failure, or user-visible interaction bug.

## Current Capability Classification

| Area | Current classification | Meets current MVP need? | Notes |
|---|---:|---:|---|
| K-line interaction | Complete | Yes | Interactive candlestick charts, range controls, and common indicator overlays are available. |
| Technical indicators | Complete | Yes | MA, BOLL, volume, MACD, RSI, and KDJ are covered by frontend/backend calculation and tests. |
| Smart recommendations | Complete as research signals | Yes for MVP | Breakout, oversold rebound, volume anomaly, and momentum-style signals exist; professional-grade backtesting is still missing. |
| Comparison analysis | Complete | Yes for MVP | Correlation-oriented comparison is available; deeper risk metrics remain future work. |
| Hot sector rotation | Provider-backed MVP | Partially | Contract, taxonomy, data modes, flow definition, top constituents, and degraded-safe UI exist; production provider verification is still needed. |
| Intraday chart | Provider-backed MVP | Partially | yfinance `1m` minute bars can return verified data; broader provider coverage, storage, session governance, and realtime push are still missing. |
| Market depth | Provider-boundary MVP | Partially | Explicit `fetch_market_depth` boundary, section-level status, real-row rendering, and large-order derivation from verified trades exist; built-in production Level-2 provider is not verified. |
| AI market assistant | MVP available | Partially | Single-symbol assistant with citations, diagnostics, and safety boundaries exists; multi-turn memory, retrieval, and realtime linkage remain future work. |

## Professional Platform Benchmark

### TradingView-style charting gap

Current platform has functional K-line charts and common technical indicators. It still lacks professional chart workspace features such as saved layouts, multi-chart grids, custom scripting, alert rules attached to chart conditions, drawing tools, and multi-timeframe synchronization.

### Bloomberg / Koyfin / AlphaSense-style research gap

Current platform has reports, fundamentals, news payloads, and an AI market assistant MVP. It still lacks broad document retrieval, earnings-call transcripts, filings search, persistent research notebooks, entity/topic search, watchlist-level narrative monitoring, and citation-rich multi-document synthesis.

### Broker / order-flow terminal gap

Current platform now has a safe market-depth boundary but does not yet have verified production Level-2, recent trades, order-flow analytics, heatmaps, execution integration, entitlement management, or low-latency streaming.

### CN retail-market terminal gap

Current platform has hot-sector and fund-flow contracts, but still lacks production-grade A-share sector breadth,涨跌家数, 成分股贡献拆解, 龙虎榜/公告 integration, market style rotation, local-market calendars, and provider-specific quota/permission governance.

## Prioritized Optimization Plan

### P0 - Keep website entry stable

- Status: completed in this task for the observed `/zh` entry point.
- Validation evidence: browser snapshot rendered the dashboard, and homepage-focused tests passed.
- Follow-up trigger: create a focused theme-provider task only if the `next-themes` warning becomes a blocking overlay or reproducible hydration bug.

### P0 - Production market-depth provider validation

- Objective: integrate or validate a real provider path for at least one of order book, recent trades, or fund-flow.
- Acceptance direction:
  - explicit `fetch_market_depth` provider method,
  - fixture-backed parser tests,
  - live-gated smoke check,
  - partial section semantics retained,
  - no daily/minute/mock fabrication.
- Trellis mapping: continue or split from `07-04-real-market-depth-provider-pipeline`.

### P0 - Intraday cache and session governance

- Objective: make the yfinance `1m` MVP more production-like by caching verified minute rows and applying trading-session/calendar rules.
- Acceptance direction:
  - persistent or cache-backed minute rows,
  - session-aware no-data reasons,
  - explicit handling for weekends/holidays/premarket/after-hours,
  - additional provider candidates behind the same `fetch_intraday_bars` boundary.
- Trellis mapping: continue or split from `07-04-real-intraday-minute-data-pipeline`.

### P1 - Hot-sector production provider and breadth metrics

- Objective: move from provider-backed contract to production-verified sector rotation signals.
- Acceptance direction:
  - verified provider for sector ranking or fund-flow,
  -涨跌家数 / breadth fields,
  - constituent contribution ranking,
  - historical sector rotation snapshots,
  - taxonomy governance across CN/HK/US where applicable.
- Trellis mapping: create a follow-up to the archived `07-04-hot-sector-fund-flow-provider` work when ready.

### P1 - AI assistant retrieval and multi-turn research context

- Objective: move the assistant beyond single-turn daily-bar context into richer research workflows.
- Acceptance direction:
  - multi-turn session context,
  - report/news/filing retrieval,
  - stronger citation display,
  - visible data freshness and provider diagnostics,
  - no trading-instruction behavior.
- Trellis mapping: create a follow-up to the AI market assistant MVP.

### P2 - Professional chart workspace

- Objective: approach TradingView-like workflows without changing the current data safety model.
- Acceptance direction:
  - saved chart layouts,
  - multi-timeframe synchronization,
  - indicator parameter persistence,
  - drawing/annotation tools,
  - chart-linked alerts.
- Trellis mapping: split from existing technical indicator and frontend polish tasks.

### P2 - Recommendation backtesting and strategy evaluation

- Objective: make smart recommendations auditable as research signals.
- Acceptance direction:
  - historical hit-rate metrics,
  - drawdown and risk statistics,
  - benchmark comparison,
  - signal explanation snapshots,
  - no automatic trading claims.
- Trellis mapping: create a new strategy-evaluation task when recommendation work resumes.

## Recommended Next Trellis Execution Order

1. Finish and archive the entry-stability/gap-plan task after recording validation evidence.
2. Continue `07-04-real-market-depth-provider-pipeline` only if the next goal is verified Level-2 / recent-trade / fund-flow provider integration.
3. Continue `07-04-real-intraday-minute-data-pipeline` only if the next goal is cache/session/provider broadening.
4. Create a focused AI assistant retrieval task when product priority shifts to research workflow depth.
5. Create chart-workspace and recommendation-backtesting tasks after market-data provider confidence improves.
