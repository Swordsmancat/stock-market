# Professional Benchmark And Trellis Execution Plan

Date: 2026-07-05

## Benchmark Sources

- TradingView emphasizes supercharts, drawing tools, alerts, watchlists, strategies, and broad market coverage: https://www.tradingview.com/features/ and https://www.tradingview.com/support/solutions/43000703396-drawing-tools-available-on-tradingview/
- Yahoo Finance advertises quotes, market news, portfolio/watchlist tools, charts, alerts, financials, and broad exchange coverage: https://finance.yahoo.com/ and https://help.yahoo.com/kb/SLN36623.html
- Bloomberg Terminal and Bloomberg PORT emphasize real-time data, news, research, analytics, execution workflow, portfolio/risk/performance analytics, and institutional data integration: https://professional.bloomberg.com/products/bloomberg-terminal/ and https://professional.bloomberg.com/products/bloomberg-terminal/portfolio-analytics/
- Eastmoney exposes professional CN-market surfaces such as market quotes, data center, sector fund-flow rankings, financing/margin data, Dragon-Tiger lists, research, announcements, and quote pages with depth/tick-style modules: https://www.eastmoney.com/default.html, https://data.eastmoney.com/bkzj/, and https://quote.eastmoney.com/center/
- Tonghuashun and Futu/Moomoo-style products emphasize Level-2, tick details, order-book/depth, sector/fund-flow analytics, watchlists, alerts, mobile/desktop sync, and trading-adjacent workflows: https://www.10jqka.com.cn/, https://www.10jqka.com.cn/ad_mar/l2_tyzx1229/zdgn_genduo.html, https://www.futuhk.com/hans/manual/topic11_65, and https://support.futunn.com/hant/topic56

## Gap Priority

| Priority | Gap | Why It Matters | Trellis Mapping |
|---:|---|---|---|
| P0 | Data reliability, cache/session metadata, provider SLA, and permission governance | Professional users must know freshness, source, entitlement, and failure state before trusting any analysis. | Existing `07-05-market-data-cache-session-governance` |
| P0 | Verified intraday pipeline beyond a yfinance MVP | Professional quote pages need reliable minute sessions, history windows, and provider fallback across markets. | Existing `07-04-real-intraday-minute-data-pipeline` |
| P0 | Verified market depth / recent trades / fund-flow pipeline | Level-2, tick details, and large-order/fund-flow analytics are major gaps versus CN terminals and broker apps. | Existing `07-04-real-market-depth-provider-pipeline` |
| P0 | AI research retrieval and citation trust | Bloomberg/Koyfin/AlphaSense-style workflows require traceable document/news/report evidence, freshness, and citation diagnostics. | Existing `07-05-ai-research-retrieval-citations` |
| P1 | Hot-sector production breadth and rotation history | Eastmoney/Tonghuashun-style sector views need verified provider data, breadth, contribution, and historical rotation. | New `07-05-hot-sector-production-breadth-rotation-history` |
| P2 | Professional chart workspace | TradingView parity needs drawing tools, saved layouts, multi-timeframe workspaces, custom formulas, and chart-linked alerts. | New `07-05-professional-chart-workspace-enhancements` |
| P2 | Recommendation backtesting and signal evaluation | Research signals need historical outcomes before users can judge reliability or compare strategies. | New `07-05-recommendation-backtesting-signal-evaluation` |
| P2 | Comparison/risk analytics enrichment | Portfolio and instrument comparison should add beta, volatility, drawdown, contribution, and saved comparison sets. | Candidate future child task after recommendation/backtesting design |

## Execution Rules

- Do not fold broad professional upgrades into this audit task.
- Each child task must start in planning and add `design.md` plus `implement.md` before activation if it spans backend, frontend, data storage, and tests.
- Provider-dependent tasks must keep degraded-safe contracts: no mock, daily-bar, or estimated data may masquerade as verified realtime, Level-2, tick, large-order, or fund-flow data.
- Documentation updates must accompany any changed endpoint contract, provider capability matrix, or user-facing data-status semantics.
- Validation should stay focused first, then run full backend/frontend regressions before closing a task.

