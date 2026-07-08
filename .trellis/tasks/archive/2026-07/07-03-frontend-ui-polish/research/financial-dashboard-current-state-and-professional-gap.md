# Research: financial dashboard current state and professional gap

- Query: 当前已实现金融 dashboard 功能是否完成；与 TradingView、Yahoo Finance、Bloomberg/MarketWatch、东方财富、同花顺等专业金融产品对比；列出应进入 Trellis 计划的 P0/P1/P2 改进项。
- Scope: mixed
- Date: 2026-07-05

## Findings

### Completion and manual-update judgment

The current `07-03-frontend-ui-polish` task should not be treated as fully complete yet.

- The task itself is still `in_progress` in `.trellis/tasks/07-03-frontend-ui-polish/task.json`.
- The PRD explicitly says the automated/code-verifiable portion is only partially complete and should not be archived because visual/manual validation is still required: `.trellis/tasks/07-03-frontend-ui-polish/prd.md:100-123`.
- The implementation notes repeat that first-viewport density, dark/light contrast, responsive behavior, secondary movement colors, and browser screenshot evidence remain before archival: `.trellis/tasks/07-03-frontend-ui-polish/implement.md:7-37`.
- Therefore, `docs/manual/user-guide.md` should not be declared fully final for this UI-polish feature yet. It already contains a useful professional-product comparison and roadmap at `docs/manual/user-guide.md:194-215`, but a future implementation/manual-update pass should refresh it only after browser validation closes the PRD acceptance criteria.

### Files found

- `README.md` - high-level platform description, key features, and Phase 2/3 status matrix; especially `README.md:82-102`.
- `docs/manual/user-guide.md` - current user-facing manual for Phase 2/3 dashboard capabilities; feature status at `docs/manual/user-guide.md:3-18`, professional comparison at `docs/manual/user-guide.md:194-215`.
- `.trellis/tasks/07-03-frontend-ui-polish/prd.md` - UI polish acceptance criteria and automated completion assessment; open criteria at `.trellis/tasks/07-03-frontend-ui-polish/prd.md:89-123`.
- `.trellis/tasks/07-03-frontend-ui-polish/design.md` - intended dense financial UI, color-scheme hook/context, settings, chart, and page-level redesign.
- `.trellis/tasks/07-03-frontend-ui-polish/implement.md` - current implementation status, validations, and remaining archival blockers.
- `.trellis/spec/frontend/index.md` - frontend patterns: Next.js App Router, server pages, route proxies, i18n, UI primitives.
- `.trellis/spec/frontend/state-management.md` - server data, URL state, server actions, and chart workspace localStorage contract.
- `.trellis/spec/backend/hot-sector-contract.md` - provider-backed hot-sector/fund-flow contract and no-fabrication rules.
- `.trellis/spec/backend/intraday-cache-contract.md` - provider-backed `1m` intraday cache contract.
- `.trellis/spec/backend/market-depth-contract.md` - explicit provider boundary for market depth, recent trades, large orders, and fund-flow sections.
- `.trellis/spec/backend/assistant-research-citation-contract.md` - AI assistant citation/diagnostic/safety contract.
- `apps/web/app/[locale]/page.tsx` - main dashboard server page.
- `apps/web/components/market-overview-client.tsx` - client refresh/auto-refresh market overview table using market color context.
- `apps/web/components/market-ticker.tsx` - Yahoo-style black market ticker with market filter.
- `apps/web/components/hot-sectors.tsx` - hot-sector/fund-flow display.
- `apps/web/components/smart-recommendations.tsx` - technical-signal recommendation display.
- `apps/web/components/comparison-tool.tsx` - comparison/correlation UI.
- `apps/web/components/advanced-candlestick-chart.tsx` - interactive daily K-line chart with technical indicators and local workspace state.
- `apps/web/components/intraday-price-chart.tsx` - intraday minute chart component.
- `apps/web/components/market-depth-card.tsx` - Level-2/depth/recent-trade/large-order/fund-flow card.
- `apps/web/components/market-assistant-card.tsx` - citation-aware AI market assistant UI.
- `apps/web/app/[locale]/instruments/[symbol]/page.tsx` and `apps/web/components/instrument-detail-client.tsx` - instrument detail page shell and client layout.
- `apps/web/app/[locale]/watchlist/page.tsx` and `apps/web/components/watchlist-forms.tsx` - watchlist table, add/remove, alert rules.
- `apps/web/app/[locale]/settings/page.tsx` - provider, LLM, AkShare/Tushare, and market color settings.
- `packages/services/market_dashboard.py` - backend aggregation for dashboard market overview.
- `packages/services/market_data.py` - daily bars, intraday bars/cache, market depth provider boundary.
- `packages/services/hot_sectors.py` - hot-sector/fund-flow provider and mock/degraded payloads.
- `packages/services/market_assistant.py` - AI assistant evidence, citations, diagnostics, and fallback behavior.
- `apps/api/routers/*.py` - API endpoints backing dashboard, market data, assistant, sectors, recommendations, reports, watchlist, portfolios, task runs, settings.

### Current implemented feature inventory

Dashboard/home page:

- Server page loads instruments and many dashboard datasets in parallel: latest bar, daily bars, reports, daily report/history, demo portfolio, indicators, fundamentals, news, task run, watchlist, alerts, and aggregated market overview (`apps/web/app/[locale]/page.tsx:641-740`).
- It builds ticker items from market indices and renders `MarketTicker` before the main dashboard body (`apps/web/app/[locale]/page.tsx:835-862`).
- It renders provider/range metadata, degraded market-overview handling, and `MarketOverviewClient` (`apps/web/app/[locale]/page.tsx:928-969`).
- It renders `SmartRecommendations`, `HotSectors`, and `ComparisonTool` on the homepage (`apps/web/app/[locale]/page.tsx:971-989`).
- It renders a followed-instrument K-line table with latest close, movement, compact chart, freshness badge, and detail links (`apps/web/app/[locale]/page.tsx:991-1082`).
- It renders valuation indicators such as Buffett-style indicators and no-data states (`apps/web/app/[locale]/page.tsx:1085-1120`).
- It renders a daily-bar command center/data-health card with fresh/stale/no-data/unavailable counts and next-action buttons (`apps/web/app/[locale]/page.tsx:1124-1199`).
- The homepage test asserts the dashboard includes core indices, recommendations, mock hot-sector metadata, comparison UI, followed K-line charts, market-data health, AI report citations, latest task run, portfolio value, ingestion, and refresh actions (`apps/web/app/[locale]/page.test.tsx:437-488`).

Market overview backend:

- The market overview service uses followed watchlist items when present, otherwise falls back to the first configured instruments (`packages/services/market_dashboard.py:118-133`).
- It returns generated time, provider, range, followed instruments, indices, valuation indicators, and diagnostics (`packages/services/market_dashboard.py:248-285`).

Color scheme / professional UI polish:

- Global `MarketColorsProvider` is wired in the localized app layout under `ThemeProvider` and `NextIntlClientProvider` (`apps/web/app/[locale]/layout.tsx:45-68`).
- Platform settings persist `color_scheme` alongside market-data and LLM providers (`packages/services/platform_settings.py:10-17`, `packages/services/platform_settings.py:130-146`; frontend store at `apps/web/lib/platform-settings-store.ts:38-45`, `apps/web/lib/platform-settings-store.ts:158-171`).
- Settings UI exposes China/international color-scheme radio choices (`apps/web/app/[locale]/settings/page.tsx:197-225`; i18n strings at `apps/web/messages/en.json:666-669`, `apps/web/messages/zh.json:678-679`).
- `MarketOverviewClient`, `MarketTicker`, and `PriceChangeBadge` use `useMarketColorsContext()` (`apps/web/components/market-overview-client.tsx:16-88`, `apps/web/components/market-ticker.tsx:5-95`, `apps/web/components/price-change-badge.tsx:4-44`).
- Some movement/domain colors remain hard-coded and need classification/follow-up: followed-K-line movement color on homepage (`apps/web/app/[locale]/page.tsx:1018`), instrument-detail absolute change (`apps/web/components/instrument-detail-client.tsx:157`), hot-sector leader/flow colors (`apps/web/components/hot-sectors.tsx:316-364`), and non-movement role colors such as bid/ask labels (`apps/web/components/market-depth-card.tsx:254-275`).

Instrument detail:

- The instrument detail client renders summary price cards, AI market assistant, market depth, intraday chart, and advanced daily K-line chart (`apps/web/components/instrument-detail-client.tsx:150-225`).
- The advanced candlestick chart uses `lightweight-charts`, supports MA/BOLL/volume/MACD/RSI/KDJ controls, time ranges, dark theme, and local chart workspace save/restore/reset via `localStorage` (`apps/web/components/advanced-candlestick-chart.tsx:4-18`, `apps/web/components/advanced-candlestick-chart.tsx:91-157`, `apps/web/components/advanced-candlestick-chart.tsx:229-668`).
- The intraday chart renders only when status is `ok` and data is present; otherwise it shows degraded/empty states (`apps/web/components/intraday-price-chart.tsx:88-246`).
- The market depth card renders top-level status, bids/asks, recent trades, large orders, fund-flow, and section-level degraded reasons (`apps/web/components/market-depth-card.tsx:184-355`).
- The market assistant card submits contextual questions and renders status, citations with metadata/excerpts, diagnostics, and safety text (`apps/web/components/market-assistant-card.tsx:21-215`).
- Detail-page tests cover enhanced detail view, real intraday payload, real market-depth rows, no-K-line fallback, and failed detail load (`apps/web/app/[locale]/instruments/[symbol]/page.test.tsx:161-356`).

Watchlist / alerts:

- Watchlist is table-based and includes symbol links, name, market, latest price, RSI, alert-rule badges/forms, detail links, and remove action (`apps/web/app/[locale]/watchlist/page.tsx:72-196`).
- Watchlist API and service endpoints support default watchlist get/upsert/delete (`apps/api/routers/watchlists.py:25-51`).
- Server actions support alert-rule update with revalidation (`apps/web/app/[locale]/actions.ts:299-315`).
- Watchlist tests cover enriched API payload rendering and alert update feedback (`apps/web/app/[locale]/watchlist/page.test.tsx:40-162`).

Backend/API capabilities:

- API routers expose health, instruments, market latest/bars/intraday/depth/indicators, market overview, sectors/hot, recommendations, assistant, reports, task runs, watchlist, alerts, portfolios, and settings (`apps/api/routers/*.py`, key endpoints enumerated by `apps/api/routers/market_data.py:39-123`, `apps/api/routers/dashboard.py:10-15`, `apps/api/routers/sectors.py:11-21`, `apps/api/routers/recommendations.py:74-153`, `apps/api/routers/assistant.py:28-34`).
- Intraday service only uses explicit `fetch_intraday_bars`, supports historical closed-session cache hit/miss/unavailable metadata, and returns provider/cache/no-data/degraded statuses (`packages/services/market_data.py:215-228`, `packages/services/market_data.py:487-630`, `packages/services/market_data.py:903-1034`).
- Market depth service only uses explicit `fetch_market_depth`, derives large orders from verified recent trades, and marks sections independently (`packages/services/market_data.py:237-250`, `packages/services/market_data.py:1230-1439`).
- Hot-sector service has provider result fields for status, `data_mode`, `flow_definition`, capabilities, and degraded/mock fallback (`packages/services/hot_sectors.py:141-170`, `packages/services/hot_sectors.py:281-423`).
- AI assistant service builds evidence from bars, indicators, fundamentals, news, and generated reports; validates unknown citation IDs; returns citations/diagnostics/safety-bounded responses (`packages/services/market_assistant.py:58-178`, `packages/services/market_assistant.py:523-535`, `packages/services/market_assistant.py:580-602`, `packages/services/market_assistant.py:681-831`).
- Smart recommendations include breakout, volume anomaly, oversold, and momentum-style generation plus deterministic evaluation diagnostics in service code (`packages/services/smart_recommendations.py:19-57`, `packages/services/smart_recommendations.py:280-350`).

Documentation state:

- README says the platform is an internal research platform for multi-market data ingestion, technical indicators, AI reports, alerts, and simulated portfolios (`README.md:1-2`).
- README lists key features: market data, analysis pipeline, watchlist alerts, portfolios, task runs, and sector rotation (`README.md:82-89`).
- README marks K-line interaction, smart recommendations, comparison analysis, and technical indicator library complete; hot sectors, intraday, market depth, and AI assistant remain partial/provider-backed MVPs (`README.md:91-102`).
- Manual status table matches that split: completed K-line/recommendations/comparison/technical indicators; provider-backed MVP hot sectors/intraday/depth; research-citation MVP AI assistant (`docs/manual/user-guide.md:11-18`).
- Manual already notes key gaps: real-time, Level-2, order flow, filings/transcripts, vector search, notebook workflow, watchlist monitoring, screener/backtest/strategy evaluation (`docs/manual/user-guide.md:190-215`).

### Comparison with professional financial products

| Dimension | Current project | Professional products commonly provide | Gap assessment |
|---|---|---|---|
| Market coverage and timeliness | Multi-market symbols, daily bars, yfinance-backed `1m` intraday when available, provider capability/degraded states. | Real-time or low-latency cross-asset data, extended hours, tick/trade prints, exchange calendars, entitlements, broad global coverage. | Strong MVP transparency, but not professional-grade real-time market data. Need production provider validation, calendars, and streaming. |
| Dashboard density | Homepage includes ticker, indices, followed K-lines, valuation indicators, data health, recommendations, sectors, comparison, reports, tasks, portfolio. | Dense multi-window workstations, configurable widgets, persistent layouts, keyboard-driven workflows, streaming updates. | Good internal research dashboard; still lacks verified first-viewport density evidence, configurable layouts, and full workstation behavior. |
| Charting | `lightweight-charts` daily K-line, range controls, MA/BOLL/volume/MACD/RSI/KDJ, local workspace note/toggles, intraday chart. | TradingView-style drawing tools, custom scripts, multi-timeframe/multi-pane sync, alerts on chart events, replay, strategy tester, cloud layout sync. | Solid chart MVP but not professional charting parity. |
| Watchlist and alerts | Watchlist table with price/RSI, add/remove, price/RSI alert rules and trigger history. | Realtime watchlists, custom columns, sorting/filtering, news/filing/technical alerts, notification channels, scanner integration. | Needs custom columns, streaming refresh, richer alert conditions, and notification delivery. |
| Screener and research discovery | Smart recommendations and comparison tool; no full condition screener route found. | Fundamental/technical screeners, heatmaps, sector maps, earnings calendars, custom scans, saved queries. | Major professional-product gap. |
| Market depth/order flow/fund flow | Explicit provider-boundary MVP for order book/recent trades/large orders/fund-flow; AkShare candidate path is not production-verified. | Production Level-2, time-and-sales, order-flow analytics, depth heatmaps, institutional flow, DDE/main-fund-flow dashboards. | Important P0/P1 gap for CN-style professional dashboards. |
| Sector rotation | Provider-backed contract with flow definition, breadth, constituent contribution, taxonomy, data-mode/status metadata; default fallback still mock/degraded. | Real sector/industry fund flow, breadth, contribution, rotation history, themes, heatmaps, constituent drill-down. | Contract is strong; real provider and historical rotation are missing. |
| News/research/fundamentals | Fundamentals, news sentiment, generated reports, AI assistant citations/diagnostics. | Professional news wires, filings/transcripts/announcements, broker research, ownership/estimates, entity/topic search, persistent notebooks. | Strong research-audit foundation; lacks production research corpus and retrieval. |
| AI assistant | Safety-bounded, citation-aware, deterministic fallback. | Commercial systems increasingly integrate document search, transcript/filing QA, watchlist monitoring, and workflow memory. | Good differentiator for internal research; needs more sources and persistent workflow. |
| Portfolio/risk | Simulated portfolios with CRUD and demo fallback. | Portfolio analytics, attribution, factor/risk exposures, scenario analysis, compliance, order/execution integration. | Current feature is research-only and portfolio analytics are shallow. |
| Operations/data trust | Provider settings, capability matrix, degraded states, readiness scripts, task runs. | Data SLA, entitlement management, audit logs, source lineage, incident monitoring. | Better than many MVPs in no-fabrication semantics, but not production operations grade. |

### Professional-product references

Public references consulted or targeted for product dimension comparison on 2026-07-05:

- TradingView official product pages: Supercharts/features, Alerts, Pine Script docs, Screener, Heatmaps: `https://www.tradingview.com/features/`, `https://www.tradingview.com/alerts/`, `https://www.tradingview.com/pine-script-docs/`, `https://www.tradingview.com/screener/`, `https://www.tradingview.com/heatmap/`.
- Yahoo Finance public product/help surface: `https://finance.yahoo.com/`, `https://help.yahoo.com/kb/finance-for-web`.
- Bloomberg Professional products: Terminal and PORT/portfolio risk analytics: `https://www.bloomberg.com/professional/products/bloomberg-terminal/`, `https://www.bloomberg.com/professional/products/portfolio-risk-analytics/`.
- MarketWatch public tools surface: `https://www.marketwatch.com/tools`.
- 东方财富 public data/quote surfaces: `https://data.eastmoney.com/`, `https://quote.eastmoney.com/center/`.
- 同花顺/iFinD public product surfaces: `https://www.51ifind.com/`, `https://www.10jqka.com.cn/ad_mar/level2/league_level2.php`.

These sources are used as broad public feature baselines, not as exhaustive product specifications or entitlement documentation.

### Should the current product satisfy the user need?

It satisfies an internal research dashboard MVP need:

- It aggregates core market data, watchlist, reports, portfolio, task runs, recommendations, hot sectors, comparison, and instrument detail workflows.
- It is unusually careful about degraded/provider states, citation provenance, and no-fabrication contracts.
- It has meaningful frontend tests across dashboard, watchlist, chart, hot sector, depth, assistant, and detail pages.

It does not yet satisfy a professional financial website/terminal parity need:

- Real-time market data, production Level-2/order-flow/fund-flow, richer sector rotation, full screeners/backtests, professional research corpus, and persistent workstation layout are incomplete or absent.
- The UI polish task is not acceptance-complete until first-viewport density, responsive behavior, contrast, and screenshot evidence are validated.
- Some movement colors still bypass the new global color context, so the color-scheme acceptance criterion is only partially closed.

### Recommended Trellis plan

P0:

1. Close `07-03-frontend-ui-polish` acceptance evidence.
   - Capture browser screenshots for desktop/tablet/mobile.
   - Prove 15+ indices/followed instruments are visible in common desktop first viewport.
   - Verify light/dark WCAG AA contrast and no overlap.
   - Classify and fix remaining hard-coded movement colors that should obey market color context.
   - Update `docs/manual/user-guide.md` and README only after this evidence exists.

2. Professional data-trust baseline.
   - Add a single dashboard-wide data provenance/freshness panel or inline contract that consistently explains live/delayed/mock/no-data across market overview, sectors, intraday, depth, reports, and assistant.
   - Ensure every mock/degraded section is impossible to confuse with real market data.

3. Production provider readiness for high-value market data.
   - Prioritize real provider validation for intraday and depth/fund-flow paths.
   - Keep explicit no-fabrication boundaries from the existing specs.
   - Add readiness/smoke evidence to task artifacts before promoting any provider capability.

P1:

1. Real depth, transaction, and fund-flow pipeline.
   - Promote a verified provider for Level-2/order book/recent trades/fund flow.
   - Add schema monitoring and capability matrix updates.
   - Add UI states for partial provider support without collapsing into generic unavailable states.

2. Sector rotation and CN-style market breadth.
   - Add real sector/industry provider, breadth, constituent contribution, rotation history, and cross-market taxonomy governance.
   - Add history snapshots so rotation is not just a current-rank card.

3. Screener/watchlist upgrade.
   - Add technical/fundamental condition screener, saved filters, sortable custom watchlist columns, and custom alert conditions.
   - Connect recommendation signals to a browsable/filterable scanner rather than only a top-N widget.

4. Professional charting upgrade.
   - Persist indicator parameters and full chart workspace layout.
   - Add drawing/annotation primitives, multi-timeframe sync, compare overlays, and alert hooks.
   - Preserve the current local-only warning unless user/account sync is implemented.

5. AI research assistant enhancement.
   - Add filings/transcripts/announcements and vector retrieval only after source ingestion and citation contracts exist.
   - Add persistent research sessions/notebooks and watchlist-level monitoring.

P2:

1. Strategy validation/backtesting.
   - Expose deterministic recommendation evaluation through API/UI.
   - Add persistent signal history, costs/slippage, portfolio-level backtests, benchmark-relative analytics, and walk-forward validation.

2. Portfolio/risk analytics.
   - Add exposure, attribution, factor/risk views, scenario analysis, and rebalance rationale.

3. Workstation personalization.
   - Add configurable dashboard layouts, saved widgets, keyboard-command coverage, exports/sharing, and cross-device workspace sync.

4. Operations and entitlement maturity.
   - Add data SLA dashboards, provider incident history, entitlement/permission model, audit logs, and provider usage monitoring.

### Related specs

- `.trellis/spec/frontend/index.md`
- `.trellis/spec/frontend/component-guidelines.md`
- `.trellis/spec/frontend/state-management.md`
- `.trellis/spec/frontend/type-safety.md`
- `.trellis/spec/frontend/quality-guidelines.md`
- `.trellis/spec/backend/index.md`
- `.trellis/spec/backend/hot-sector-contract.md`
- `.trellis/spec/backend/intraday-cache-contract.md`
- `.trellis/spec/backend/market-depth-contract.md`
- `.trellis/spec/backend/assistant-research-citation-contract.md`

## Caveats / Not Found

- No browser visual validation was run in this research pass; conclusions about UI completion rely on task artifacts and code/tests, not screenshots.
- No tests, type-check, or dev server were run because this was a read-only research task and another agent is concurrently handling type-check fixes.
- No source or documentation files outside `.trellis/tasks/07-03-frontend-ui-polish/research/` were modified.
- Public professional-product pages change frequently and often omit entitlement details; comparison is dimension-level, not an exact feature-by-feature license audit.
- Search found no full professional screener/backtest/workstation-layout implementation in app code; existing docs also list these as future gaps (`docs/manual/user-guide.md:204-215`).

## 2026-07-05 follow-up evidence update

This research file originally predated the dedicated browser evidence pass. The evidence-only UI gap described above was later closed by `07-05-dashboard-visual-evidence-wcag`:

- durable screenshots were captured for `/zh`, `/zh/settings`, `/zh/instruments/AAPL`, and `/zh/watchlist` at `1440x900` and `390x844`;
- browser observations recorded no console errors, no runtime-error text, and no document/body horizontal overflow on sampled routes;
- light/dark computed-style contrast samples passed WCAG AA for sampled text sizes after the black ticker neutral text was changed to `text-gray-300`.

This update closes the UI evidence gap for the sampled MVP routes, but it does not change the professional-terminal parity conclusion. Realtime feeds, production Level-2/order-flow/fund-flow validation, richer sector rotation, full screeners/backtests, professional research corpus, and persistent workstation layout remain future professional gaps.
- PowerShell raw output displayed mojibake for some Chinese markdown during full-file reads, but `rg` confirmed readable UTF-8 content and line references in `docs/manual/user-guide.md`. A future docs-edit pass should verify encoding in the editor before changing manual text.
