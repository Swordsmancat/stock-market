# Professional Benchmark Research - 2026-07-05

## Sources Checked

- TradingView official feature/support pages: customizable layouts, multi-chart layouts, drawing tools, alerts, screeners, calendars, and trading tools.
- Bloomberg Professional official pages: Terminal real-time data, news, analytics, charts, collaboration, research, execution, and portfolio analytics.
- LSEG official pages: Workspace insights, news, analytics, datasets, Reuters/Dow Jones news coverage, research workflows, and productivity tools.
- Yahoo Finance public pages/app listings: quotes, news, watchlists, portfolios, personalized alerts, and broad asset coverage.
- Eastmoney Choice official pages/listings: all-category market data, macro/industry/company data, research information, AI research assistant, fund flow, news/reports, and terminal/data/API products.
- Tonghuashun iFinD public pages/listings: global market quotes, news/research, fundamentals, macro/industry databases, data browser, research tools, and PC/mobile linkage.
- Moomoo public help/learn pages: Level-2 data, charts, stock analysis, screeners, alerts, and desktop/mobile workflows.

## Current Product Fit

The current implementation is sufficient for an MVP financial research dashboard:

- Localized dashboard and navigation.
- Market overview, watchlist/default samples, quotes, daily bars, freshness, and provider metadata.
- Instrument detail with daily chart, intraday chart, technical indicators, market-depth boundary, AI assistant, reports, news/fundamentals, and related actions.
- Hot-sector, recommendation, and comparison surfaces with degraded-safe provider semantics.
- AI research citations and diagnostics.
- User and maintainer documentation for research-only and degraded-safe behavior.

It should not be positioned as a professional terminal equivalent.

## Gap Summary

| Priority | Gap | Professional reference pattern | Recommended Trellis execution |
|---|---|---|---|
| P0 | Verified realtime and provider trust | Bloomberg/LSEG/Choice/iFinD/Moomoo emphasize realtime data, Level-2, fund flow, and broad asset coverage. | Continue market-data reliability, provider live smoke, calendar/session governance, cache persistence, and entitlement-safe depth tasks. |
| P0 | Level-2 / order-flow production data | Moomoo and CN terminals expose Level-2 order books; Choice/iFinD advertise Level-2 and fund-flow analytics. | Keep current depth boundary; only promote order book/recent trades/fund flow after reachable provider smoke and schema capture. |
| P1 | Research retrieval depth | Bloomberg/LSEG/Choice/iFinD integrate news, research, filings/announcements, macro/industry/company databases, and AI research workflows. | Add filings/transcripts/announcements/research-feed retrieval, source scoring, and persistent research sessions. |
| P1 | China-market breadth and sector rotation | Choice/iFinD emphasize sector, fund flow, macro/industry databases, and CN market analytics. | Persist sector rotation snapshots, verify provider breadth/constituent contribution, and add Dragon-Tiger/announcement integration when providers support it. |
| P2 | Professional chart workspace | TradingView emphasizes layouts, multi-chart analysis, drawing tools, screeners, alerts, and rich chart customization. | Extend chart workspace with multi-pane layouts, drawing tools, indicator parameters, comparison overlays, alerts, and optional account sync. |
| P2 | Portfolio/watchlist analytics | Bloomberg/Yahoo/Moomoo workflows include watchlists, portfolios, alerts, screeners, and performance tracking. | Add realtime watchlist monitoring, alert delivery, portfolio attribution, risk summaries, and screener workflows. |

## Decision

Archive the Phase 2/3 MVP completion task as done. Keep professional parity work as separate Trellis tasks because it is broad, provider-dependent, and independently testable.

Reference URLs:

- https://www.tradingview.com/features/
- https://www.tradingview.com/support/solutions/43000629990-leveraging-multi-chart-layouts-in-your-analysis/
- https://www.tradingview.com/support/solutions/43000703396-drawing-tools-available-on-tradingview/
- https://professional.bloomberg.com/products/bloomberg-terminal/
- https://professional.bloomberg.com/products/bloomberg-terminal/research/bloomberg-intelligence/
- https://www.lseg.com/en/data-analytics/products/workspace
- https://www.lseg.com/en/data-analytics/financial-news-service
- https://finance.yahoo.com/
- https://finance.yahoo.com/portfolios/
- https://choice.eastmoney.com/
- https://choice.eastmoney.com/terminal
- https://ft.10jqka.com.cn/
- https://www.moomoo.com/us/support/categories/1735
- https://www.moomoo.com/us/support/topic3_636
- https://www.moomoo.com/us/learn/detail-how-to-read-level-2-market-data-using-an-order-book-for-trading-strategies-66157-220709059
