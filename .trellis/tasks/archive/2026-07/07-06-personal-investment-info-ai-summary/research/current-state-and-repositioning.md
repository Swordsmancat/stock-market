# Current State And Repositioning Research

## Confirmed Current Capabilities

- Dashboard aggregation exists in `apps/web/app/[locale]/page.tsx`: market overview, valuation indicators, followed instruments, recommendations, hot sectors, reports, news, fundamentals, task runs, and freshness states.
- Backend market overview is aggregated by `packages/services/market_dashboard.py` and exposed through `apps/api/routers/dashboard.py`.
- Buffett Indicator definitions for CN/HK/US exist in `packages/services/market_indicators.py`.
- `packages/services/market_indicators.py` intentionally seeds definitions without default observations, so the UI returns no-data until audited values are added.
- `packages/domain/models.py` includes `MarketIndicator` and `MarketIndicatorObservation`, enough for a source-aware macro/valuation MVP.
- `packages/services/market_assistant.py` already implements citation-aware, no-data-aware AI assistant behavior and deterministic fallback.
- `apps/web/app/[locale]/reports/page.tsx` and `apps/web/app/[locale]/reports/[reportId]/page.tsx` provide generated report history and report detail views.

## Gaps Against Revised Direction

- Macro indicators beyond Buffett Indicator are not implemented as first-class definitions.
- Buffett Indicator observations are not populated by default; current behavior is correct but incomplete.
- There is no dashboard-level AI brief that synthesizes macro + watchlist + news + reports.
- The AI assistant scope is instrument-level, not personal dashboard/watchlist/macro scope.
- Hard-to-find source collection is not yet specified by source type, legal boundary, or freshness policy.
- README/manual still reflect a mixed "research dashboard vs professional terminal gap" narrative.

## Professional Information Platform Benchmark

Use these as inspiration, not parity targets:

- Bloomberg/Koyfin-style products demonstrate breadth: macro, markets, news, charts, dashboards, and cross-asset context.
- AlphaSense-style products demonstrate AI search and summarization over financial documents, filings, transcripts, news, and research.
- Yahoo Finance/MarketWatch/TradingView-style products demonstrate accessible personal watchlists, portfolios, screeners, charts, and news flows.
- FRED/World Bank/OECD-style public sources are more relevant to this product than trading terminals because they can supply auditable macro series.

The local product advantage should be a smaller, personal, source-transparent, AI-summarized cockpit.

## Recommended Plan

P0:

- Reposition docs and dashboard copy.
- Expand macro/valuation indicator definitions.
- Add audited seed/import flow for initial observations.
- Add deterministic daily brief from existing evidence.

P1:

- Add citation-aware dashboard AI brief.
- Add watchlist and macro digest history.
- Add official macro source adapters.

P2:

- Add personal research notes.
- Add indicator alerts.
- Add richer document ingestion and saved AI follow-ups.
