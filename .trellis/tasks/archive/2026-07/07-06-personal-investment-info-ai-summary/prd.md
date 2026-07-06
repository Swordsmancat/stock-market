# Personal Investment Information Aggregation and AI Summary Platform

## Goal

Redirect the product from professional trading-terminal parity toward a personal investment research cockpit: aggregate market, macro, valuation, news, and hard-to-find research information, then use AI to summarize what changed, why it matters, what is missing, and what a personal investor should watch next.

This task is a planning parent. It should not start implementation until the PRD/design/implementation plan is reviewed and the next slice is selected.

## Background

The user clarified the core product direction on 2026-07-06:

- The site is for personal use as an information summary and AI interpretation tool.
- The most important need is information aggregation, especially macro indicators and data that is not easy to collect from common online platforms.
- AI recommendation and summary should be the product highlight.
- The product should not compete with professional trading terminals or professional transaction platforms.

Repository evidence shows that the current platform already has useful building blocks:

- Dashboard market overview aggregates followed instruments, core indices, provider freshness, valuation indicators, reports, recommendations, news, and operational state in `apps/web/app/[locale]/page.tsx`.
- The backend dashboard payload includes `valuation_indicators` and calls `get_buffett_indicator_payloads` in `packages/services/market_dashboard.py`.
- Buffett Indicator definitions for CN/HK/US exist in `packages/services/market_indicators.py`, backed by `market_indicators` and `market_indicator_observations` tables in `packages/domain/models.py`.
- The current Buffett Indicator implementation intentionally returns `no_data` until audited observations are seeded, which matches the no-fabrication requirement.
- The AI market assistant is citation-aware and safety-bounded through `apps/api/routers/assistant.py` and `packages/services/market_assistant.py`.
- Generated reports, report citations, news sentiment, fundamentals, recommendations, watchlists, alerts, portfolios, hot sectors, intraday, and depth provider boundaries already exist.

The previous professional-dashboard roadmap overemphasized terminal parity: Level-2, real-time feeds, order-flow, backtesting, configurable workstations, and professional screeners. Those remain optional future extensions, not the main product thesis.

## Requirements

### R1. Reposition the Product

- Describe the platform as a personal investment information aggregation and AI research assistant.
- Keep "not investment advice", "no automatic trading", and "no fabricated market data" as product boundaries.
- De-emphasize terminal-grade language unless describing out-of-scope or future optional work.
- Map existing features to the new positioning instead of discarding them.

### R2. Macro and Valuation Indicator Library

- Expand the current `market_indicators` model from Buffett Indicator definitions into a broader macro/valuation library.
- Candidate P0 indicators:
  - Buffett Indicator by region.
  - Equity valuation percentile or market-cap/GDP history where sourceable.
  - 10Y/2Y yield levels and curve spread.
  - CPI/PPI/inflation trend.
  - policy rate or central-bank rate proxy.
  - M2/credit growth.
  - PMI/unemployment where regionally useful.
  - equity risk premium or stock-bond attractiveness where components are auditable.
- Every observation must expose source, as-of date, components, method note, and freshness status.
- If an indicator cannot be sourced or audited, show `no_data` with a clear reason.

### R3. Hard-to-Find Information Collection

- Prioritize data that is valuable but scattered:
  - macro and valuation series from public APIs or curated seed files.
  - earnings/filing/announcement/transcript summaries where legally accessible.
  - sector/fund-flow metadata with provider methodology.
  - watchlist-specific news/event changes.
  - AI-curated "missing data" notes when the platform lacks source coverage.
- Do not scrape or store content in ways that violate source terms; prefer official APIs, licensed providers, user-provided files, or link-and-summary workflows.

### R4. AI Daily and Weekly Summary Layer

- Add AI summaries above raw widgets:
  - "what changed"
  - "why it matters"
  - "what to watch next"
  - "evidence and citations"
  - "data gaps and freshness warnings"
  - "risk notes"
- AI should synthesize across macro indicators, watchlist movements, news, reports, sector/fund-flow metadata, and user notes.
- AI recommendations must be framed as research hypotheses, not buy/sell instructions.
- AI answers must cite retrieved evidence and degrade to deterministic summaries when LLM configuration or sources are unavailable.

### R5. Personal Research Workflow

- Support a personal daily/weekly cockpit rather than a terminal workspace:
  - one dashboard for macro + watchlist + AI summary.
  - report center for generated summaries.
  - saved personal notes or observations.
  - watchlist-focused monitoring and alerts.
  - source/freshness diagnostics visible near each insight.
- Existing charting, recommendations, reports, watchlists, and portfolio modules should become evidence inputs to the AI summary, not the primary selling point.

### R6. Documentation and Roadmap Rewrite

- Update README and user manual after the planning scope is approved.
- Preserve accurate current-state docs for existing implemented features.
- Rewrite professional-comparison sections to benchmark information aggregation and AI research workflows rather than terminal parity.
- Keep remaining terminal-grade capabilities in a clearly labeled "optional later" section.

## Current Capability Assessment

| Capability | Current state | Fit with revised direction |
|---|---|---|
| Market overview and watchlist | Implemented dashboard and provider freshness states | Useful as one input layer |
| Buffett Indicator | Definitions and no-fabrication observation model exist; no default audited observations | Strong seed for macro/valuation library, but needs real source pipeline |
| Broader macro indicators | Not implemented as a user-visible library | P0/P1 gap |
| Reports center | Implemented generated report list/detail pages | Useful for AI summaries and history |
| AI assistant | Citation-aware MVP for instrument-level context | Needs dashboard/macro/watchlist scope |
| News sentiment | Stored-symbol news sentiment MVP | Needs broader source coverage and event summaries |
| Recommendations | Technical signal cards and service evaluation foundation | Should be reframed as research leads |
| Trading-terminal features | Intraday/depth/hot-sector provider boundaries, chart indicators | Optional supporting context, not core product goal |

## Professional Platform Comparison

The revised benchmark should compare against information and research products:

- Koyfin/Bloomberg: broad market and macro data aggregation, dashboards, charts, news, and research workflow breadth.
- AlphaSense: AI search/summarization over filings, transcripts, news, and premium research.
- Yahoo Finance/MarketWatch/TradingView: personal watchlists, portfolios, news, screeners, charts, and accessible market context.
- FRED/World Bank/OECD-style public data sources: official macro series and documented APIs.

The product does not need to match their live-feed depth, entitlements, institutional corpus, or broker workflows. The local competitive angle is a personal, citation-aware AI layer over a curated set of hard-to-gather sources.

## Out of Scope

- Real-money trading, broker integration, or automatic order placement.
- Professional terminal parity as a near-term goal.
- Low-latency feeds, Level-2/order-flow heatmaps, and entitlement management unless later chosen as a separate task.
- Large-scale web scraping without source permission.
- Personalized financial advice or guaranteed returns.

## Acceptance Criteria

- [x] The current implementation is mapped to the revised personal-information/AI-summary positioning.
- [x] `design.md` describes the target information architecture, source contracts, macro indicator model, AI summary flow, and migration path from current code.
- [x] `implement.md` breaks the work into P0/P1/P2 slices with validation commands and documentation updates.
- [x] Professional comparison is reframed around information aggregation and AI research, not trading-terminal competition.
- [x] README/manual update scope is identified for the next implementation slice.
- [x] At least one high-value MVP decision is presented to the user before starting implementation.
- [x] No implementation is started until the user approves the selected slice.

## Selected First Slice

The user confirmed on 2026-07-06 that the first implementation slice should prioritize **macro/valuation indicators + AI daily/weekly summary**.

Child task created: `.trellis/tasks/07-06-macro-valuation-ai-brief-mvp`.

Implementation must still wait for review/approval of that child task's artifacts before `task.py start`.
