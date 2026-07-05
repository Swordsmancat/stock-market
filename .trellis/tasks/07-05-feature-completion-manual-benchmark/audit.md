# Feature Completion Audit

Date: 2026-07-05

## Scope And Evidence

This audit reconstructs completion from the current worktree, not from prior chat history. Evidence inspected:

- Active Trellis task tree from `python ./.trellis/scripts/get_context.py` and `task.py list`.
- Product documentation in `README.md`, `docs/manual/user-guide.md`, and `docs/runbooks/developer-maintenance.md`.
- Frontend routes/components under `apps/web/app/[locale]`, `apps/web/app/api`, `apps/web/components`, and `apps/web/lib`.
- Backend routers/services/providers under `apps/api/routers`, `packages/services`, `packages/providers`, and `scripts/provider_readiness.py`.
- Focused and full backend/frontend test runs.

## Completion Matrix

| Area | Status | Evidence | Remaining Gap |
|---|---|---|---|
| Market overview and navigation | Complete for MVP | `apps/web/app/[locale]/page.tsx`, `packages/services/market_dashboard.py`, `apps/web/components/sidebar-navigation.tsx`, `apps/web/components/global-search.tsx`, page/API tests | Professional personalization, saved dashboards, richer market breadth, and realtime push remain. |
| Individual security detail | Complete for MVP | `apps/web/app/[locale]/instruments/[symbol]/page.tsx`, `apps/web/components/instrument-detail-client.tsx`, `apps/web/lib/instrument-detail.ts`, route/page tests | Layout/workspace persistence and deeper quote modules remain. |
| Historical K-line chart and indicators | Complete for MVP | `apps/web/components/advanced-candlestick-chart.tsx`, `apps/web/lib/chart-indicators.ts`, `packages/analytics/indicators.py`, `packages/services/indicators.py`, chart/indicator tests | TradingView-style drawing tools, saved layouts, custom formulas, multi-pane workspaces, and chart-linked alerts remain. |
| Smart recommendations | Complete as research-signal MVP | `packages/services/smart_recommendations.py`, `apps/api/routers/recommendations.py`, `apps/web/components/smart-recommendations.tsx`, recommendation tests | Backtesting, hit rate, drawdown, benchmark comparison, and explainable signal history remain. |
| Comparison analysis | Complete for MVP | `apps/web/components/comparison-tool.tsx`, `apps/web/lib/comparison-utils.ts`, comparison tests | Deeper risk metrics, saved comparison sets, and portfolio/watchlist comparison workflows remain. |
| Hot sector and fund-flow view | Provider-backed MVP | `packages/services/hot_sectors.py`, `apps/api/routers/sectors.py`, `apps/web/app/api/hot-sectors/route.ts`, `apps/web/components/hot-sectors.tsx`, service/API/proxy/component/page tests | Production provider verification, breadth metrics, constituent contribution, taxonomy governance, and rotation history remain. |
| Intraday chart | Provider-backed MVP | `ProviderIntradayBar`, `YFinanceProvider.fetch_intraday_bars`, `get_intraday_bars_payload`, `IntradayPriceChart`, provider/service/API/proxy/page tests | More providers, minute-bar cache/storage, trading-session governance, longer history, and streaming refresh remain. |
| Market depth / order-flow view | Provider-boundary MVP | `ProviderMarketDepthSnapshot`, `AkShareProvider.fetch_market_depth`, `get_market_depth_payload`, `MarketDepthCard`, depth provider/service/API/proxy/page/component tests | Production-verified Level-2, recent trades, fund-flow, entitlements, schema monitoring, and order-flow analytics remain. |
| AI market assistant | Research-citation MVP | `packages/services/market_assistant.py`, `apps/api/routers/assistant.py`, `apps/web/components/market-assistant-card.tsx`, assistant tests | Multi-turn sessions, filings/transcripts/announcements, vector retrieval, notebook workflow, and watchlist narrative monitoring remain. |
| Data reliability and provider governance | Partial / active follow-up | `scripts/provider_readiness.py`, provider readiness tests, active task `07-05-market-data-cache-session-governance` | Cache/session metadata, provider SLA, quota/permission governance, and production observability remain. |
| Watchlists, alerts, portfolios, reports, task runs | Complete for MVP | `/watchlist`, `/alerts`, `/portfolios`, `/reports`, `/task-runs` pages and corresponding backend routers/services/tests | Broker-grade execution, portfolio risk attribution, alert backtesting, and richer report retrieval remain. |
| Manuals and maintenance docs | Complete for current MVP | README documentation table/status matrix, `docs/manual/user-guide.md`, `docs/runbooks/developer-maintenance.md` | Keep docs synced when follow-up tasks change endpoint contracts or provider capabilities. |

## Implementation Actions Taken In This Task

- Activated the existing Trellis task `07-05-feature-completion-manual-benchmark`.
- Fixed full backend regression failures discovered during audit:
  - `packages/services/portfolios.py` now keeps the legacy no-session demo portfolio deterministic by explicitly using the mock provider.
  - `tests/analytics/test_indicators.py` now asserts MACD values against exact unrounded expected values.
  - `tests/api/test_instruments_api.py` now isolates the seed-fallback test from local database contents.
  - `tests/services/test_market_dashboard_service.py` now clears dashboard cache before each isolated service test.
- Created follow-up Trellis child tasks for professional gaps not already covered by active tasks:
  - `07-05-hot-sector-production-breadth-rotation-history`
  - `07-05-professional-chart-workspace-enhancements`
  - `07-05-recommendation-backtesting-signal-evaluation`

## Validation

- Focused backend financial-feature regression:
  `python -m pytest tests/ai/test_market_assistant.py tests/api/test_assistant_api.py tests/api/test_market_data_intraday_api.py tests/api/test_market_depth_api.py tests/api/test_sectors_api.py tests/providers/test_cn_market_providers.py tests/providers/test_yfinance_provider.py tests/scripts/test_provider_readiness.py tests/services/test_hot_sectors_service.py tests/services/test_market_data_service.py -q`
  -> `91 passed`
- Focused frontend financial-feature regression:
  `npm run test:web -- apps/web/app/api/assistant/market/route.test.ts apps/web/components/market-assistant-card.test.tsx apps/web/app/api/hot-sectors/route.test.ts apps/web/components/hot-sectors.test.tsx apps/web/app/api/instruments/[symbol]/route.test.ts apps/web/app/[locale]/instruments/[symbol]/page.test.tsx apps/web/components/market-depth-card.test.tsx apps/web/components/intraday-price-chart.test.tsx apps/web/app/[locale]/page.test.tsx apps/web/components/advanced-candlestick-chart.test.tsx apps/web/lib/chart-indicators.test.ts`
  -> `11 passed`, `47 passed`
- Full backend regression:
  `python -m pytest -q`
  -> `276 passed`, `3 warnings`
- Full frontend regression:
  `npm run test:web`
  -> `29 passed`, `98 passed`
- Focused lint:
  `python -m ruff check packages/services/portfolios.py tests/analytics/test_indicators.py tests/api/test_instruments_api.py tests/services/test_market_dashboard_service.py`
  -> `All checks passed`

Known non-blocking warning: `packages/shared/cache.py` uses Redis `setex`, which emits a deprecation warning. It does not block this audit, but should be addressed in a future reliability/maintenance slice.

## Conclusion

The current worktree satisfies the core MVP for the requested financial dashboard and analysis workflows. The product should not be described as professionally equivalent to TradingView, Bloomberg/Koyfin/AlphaSense, Eastmoney/Tonghuashun, or Futu/Moomoo. The remaining work is broad professionalization, not a single missing feature hole, and is now mapped to Trellis follow-up tasks.
