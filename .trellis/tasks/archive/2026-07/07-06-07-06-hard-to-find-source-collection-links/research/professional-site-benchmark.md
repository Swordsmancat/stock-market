# Research: professional-site-benchmark

- Query: Compare the current personal investment research cockpit against established financial information and research sites, with emphasis on macro/valuation indicators, hard-to-find source collection, AI summaries, and boundaries that avoid professional trading terminal scope.
- Scope: mixed
- Date: 2026-07-06

## Findings

### Files found

- `README.md` - product positioning, implemented feature matrix, macro/source readiness status, and non-terminal boundary.
- `docs/manual/user-guide.md` - user-facing capability explanations and professional-site comparison notes.
- `docs/runbooks/developer-maintenance.md` - endpoint catalog, provider capability matrix, degraded-safe contracts, and roadmap gaps.
- `.trellis/tasks/07-06-07-06-hard-to-find-source-collection-links/prd.md` - task requirements for collection links, citation boundaries, and no-scraping/no-terminal scope.
- `.trellis/tasks/07-06-07-06-hard-to-find-source-collection-links/design.md` - additive payload shape for `collection_links`, `collection_note`, and `citation_policy`.
- `packages/services/information_sources.py` - source readiness registry and new collection-guidance payload fields.
- `packages/services/market_dashboard.py` - dashboard payload assembly and citation-aware narrative prompt boundary.
- `packages/services/market_indicators.py` - curated macro/valuation indicator definitions and audited manual seed import validation.
- `apps/web/app/[locale]/page.tsx` - homepage source-readiness rendering, collection notes, citation policy, and external links.
- `tests/services/test_information_sources_service.py` - backend coverage for FRED, Buffett components, and future SEC/document source guidance.
- `apps/web/app/[locale]/page.test.tsx` - frontend coverage for collection guidance labels and safe external links.

### Current implementation summary

The product is already correctly positioned as a personal research cockpit rather than a professional terminal. README states the product direction is source-transparent research aggregation, not terminal competition (`README.md:3`). Implemented capabilities include provider-backed market data, watchlists, reports, news/fundamentals context, provider diagnostics, task runs, source readiness, macro/valuation indicators, audited macro seed import, citation-aware AI summaries, recommendations, alerts, portfolios, sector rotation, charting, intraday MVP, and market-depth boundaries (`README.md:84`, `README.md:96`, `README.md:102`, `README.md:113`).

For this task, the source registry has already gained the right product primitive: `SourceCollectionLink`, `collection_note`, `citation_policy`, and `collection_links` are part of source definitions (`packages/services/information_sources.py:33`, `packages/services/information_sources.py:48`, `packages/services/information_sources.py:58`). The readiness payload is additive and returns those fields without changing evidence counting (`packages/services/information_sources.py:426`, `packages/services/information_sources.py:437`, `packages/services/information_sources.py:449`).

The FRED rates entry is a good pattern: it names official series, instructs the user to store reviewed values with source URLs and methodology, and explicitly says FRED links are collection guidance only until reviewed observations are stored locally (`packages/services/information_sources.py:93`, `packages/services/information_sources.py:112`, `packages/services/information_sources.py:116`, `packages/services/information_sources.py:120`).

The macro indicator layer is definitions-first and no-data-safe. Buffett, US yield, CPI, US M2, and China M2 definitions exist (`packages/services/market_indicators.py:89`), but default observations intentionally remain empty until verified seed files or operator-provided seeds are loaded (`packages/services/market_indicators.py:173`). Seed imports require source reference metadata and method/review metadata (`packages/services/market_indicators.py:394`, `.trellis/spec/backend/market-indicator-seed-import-contract.md:40`, `.trellis/spec/backend/market-indicator-seed-import-contract.md:47`).

The AI boundary is strong and should be preserved. The dashboard prompt tells the model not to invent market data, macro observations, filings, transcripts, realtime feeds, order flow, or source adapters, and not to treat source-readiness gaps as citations (`packages/services/market_dashboard.py:627`, `packages/services/market_dashboard.py:635`, `packages/services/market_dashboard.py:645`, `packages/services/market_dashboard.py:649`). The assistant spec similarly limits citable evidence to platform evidence and requires unknown citation IDs to degrade or fall back (`.trellis/spec/backend/assistant-research-citation-contract.md:24`, `.trellis/spec/backend/assistant-research-citation-contract.md:26`, `.trellis/spec/backend/assistant-research-citation-contract.md:30`, `.trellis/spec/backend/assistant-research-citation-contract.md:32`).

Frontend exposure is present: the homepage renders source-readiness groups, collection notes, citation policies, and safe external links with `target="_blank"` and `rel="noreferrer"` (`apps/web/app/[locale]/page.tsx:1246`, `apps/web/app/[locale]/page.tsx:1297`, `apps/web/app/[locale]/page.tsx:1305`, `apps/web/app/[locale]/page.tsx:1313`, `apps/web/app/[locale]/page.tsx:1320`). Tests verify FRED links, external-link attributes, Buffett manual guidance, and SEC future-document citation boundaries (`tests/services/test_information_sources_service.py:85`, `tests/services/test_information_sources_service.py:122`, `tests/services/test_information_sources_service.py:152`, `apps/web/app/[locale]/page.test.tsx:601`).

### External references

- [FRED](https://fred.stlouisfed.org/) and [FRED API series observations](https://fred.stlouisfed.org/docs/api/fred/series_observations.html): best model for official macro time series, stable series IDs, observations API, source naming, release cadence, and reproducible macro references. Copy the series-ID/source/as-of discipline. Do not imply adapter coverage until implemented.
- [MacroMicro](https://en.macromicro.me/): benchmark for macro dashboards, curated economic charts, market-cycle narratives, and macro-indicator explainers. Copy the curated chart-library feel and cross-indicator interpretation, but keep source gaps and methodology visible.
- [Koyfin](https://www.koyfin.com/): benchmark for personal/professional research dashboards with watchlists, market dashboards, macro data, company data, screeners, transcripts, news, and charting. Copy dashboard organization, watchlist-centric workflows, and macro/security cross-navigation. Avoid trying to match institutional data breadth.
- [TradingView features](https://www.tradingview.com/features/): benchmark for excellent chart UX, indicators, alerts, screeners, Pine Script, community ideas, and broker connectivity. Copy chart ergonomics, saved layouts, alert clarity, and screener usability. Avoid broker execution, low-latency claims, and script marketplace scope.
- [AlphaSense financial research platform](https://www.alpha-sense.com/solutions/financial-research-platform/): benchmark for AI-assisted search over filings, broker research, transcripts, expert calls, and news with citations. Copy citable document snippets, saved research trails, source filters, and summary-with-evidence patterns. Avoid proprietary content ingestion without licensing.
- [Bloomberg Terminal](https://professional.bloomberg.com/products/bloomberg-terminal/): benchmark for breadth across real-time data, news, analytics, collaboration, portfolio/risk, research, and execution workflows. Copy data provenance, freshness, diagnostics, and workflow density only where useful. Avoid terminal parity, execution, entitlements, and low-latency market-data obligations.
- [SEC EDGAR search](https://www.sec.gov/search-filings) and [SEC EDGAR APIs](https://www.sec.gov/edgar/sec-api-documentation): official/legal path for filings discovery and metadata. Copy linkout, company search, filing metadata, and eventual adapter planning. Do not store or summarize filings until ingestion, licensing, and citation metadata are implemented.
- [World Bank market capitalization to GDP](https://data.worldbank.org/indicator/CM.MKT.LCAP.GD.ZS) and [World Bank GDP](https://data.worldbank.org/indicator/NY.GDP.MKTP.CD): useful public components for Buffett-style valuation seeds. Copy component-level source links and formula transparency, not black-box valuation scores.
- [People's Bank of China](https://www.pbc.gov.cn/en/3688006/index.html): official source candidate for China monetary statistics. Treat as manual-review or adapter-candidate source until a tested ingestion path exists.

### Capability comparison

| Capability | Current product | Benchmarks | Product call |
|---|---|---|---|
| Macro/valuation indicators | Definitions-first Buffett/rates/CPI/M2 with no-data-safe display and audited seed import | FRED, MacroMicro, Koyfin | Copy official series IDs, chart libraries, release calendars, component formulas, and source/as-of metadata. |
| Source collection | Source-readiness registry now exposes official/legal links, collection notes, and citation policy | FRED, SEC EDGAR, World Bank, PBOC | This is a differentiator for a personal AI aggregator. Make it a workflow, not just static links. |
| AI summaries | Citation-aware dashboard narrative and market assistant with deterministic fallback | AlphaSense, Bloomberg AI/search workflows | Keep evidence-first. Add saved research trails and document snippets before adding more model complexity. |
| Watchlists/dashboard | Homepage aggregates ticker, overview, watchlists, recommendations, reports, source readiness, task status | Koyfin, Yahoo Finance, TradingView | Copy saved views, compact density, source/freshness badges, and watchlist-triggered brief updates. |
| Charting | Daily K-line, technical overlays, intraday MVP, local workspace notes | TradingView | Improve research-grade chart workspace and annotations. Avoid scripting marketplace and broker integration. |
| Screening/recommendations | Research-safe deterministic signals and historical evaluation foundations | Koyfin, TradingView screeners | Build a screener-lite with evidence, sample size, diagnostics, and saved criteria. Do not market outputs as trade calls. |
| Documents/transcripts | Future source guidance exists; no production filings/transcript ingestion | AlphaSense, Bloomberg, SEC EDGAR | Start with legal linkout, filing metadata, and manual reading queue. Add local document evidence only after citation and rights policy. |
| Real-time/depth/execution | Intraday/depth provider boundaries exist, with degraded states | Bloomberg, TradingView, broker terminals | Keep as secondary. Do not prioritize Level-2, order flow, execution, or realtime feed parity for this product direction. |

### What to copy

1. Official-source discipline from FRED/SEC/World Bank/PBOC: stable IDs, source URLs, release/as-of dates, methodology notes, and separate "candidate source" vs "citable local evidence" states.
2. Macro dashboard curation from MacroMicro/Koyfin: indicator families, comparison charts, release calendar, default viewpoints, and context notes explaining why an indicator matters.
3. Watchlist and workspace ergonomics from Koyfin/Yahoo/TradingView: saved dashboards, compact tables, alerts, and links from a symbol or macro event into related reports, charts, and source gaps.
4. Chart interaction patterns from TradingView: saved layouts, multi-timeframe comparisons, annotation persistence, alert markers, and clear indicator controls.
5. AI research patterns from AlphaSense: citation-filtered answers, document snippets, source filters, saved searches, and "what changed" summaries tied to evidence.

### What to avoid

1. Broker/execution workflows: order tickets, broker connections, routing, position sizing, margin, or trade recommendations.
2. Low-latency terminal promises: realtime feed SLAs, Level-2/order-book heatmaps, tick-by-tick replay, or professional entitlement management as near-term goals.
3. Unlicensed document collection: scraped filings/transcripts/research PDFs without rights, source metadata, and retention policy.
4. Citation inflation: treating source-readiness links, future adapters, or manual notes as evidence before local reviewed data exists.
5. Terminal-layout complexity: dense multi-monitor workstation features before the core personal research workflow is stable.

### Prioritized improvement plan

P0 - Make collection guidance operational.

- Add a source detail drawer/page from each readiness item with: official links, collection checklist, required seed fields, sample seed row, last local evidence, and "why not citable yet."
- Generate seed templates for FRED rates/CPI/M2 and Buffett components using existing `code`, `source_url`, `source_series_id`, `methodology`, and `review_note` requirements.
- Add release/freshness hints for macro sources: daily Treasury rates, monthly CPI/M2 style updates, World Bank annual components, and "manual review required" status.
- Keep links as guidance only. The next UI should visually separate "collect here" from "cited evidence."

P1 - Add official macro adapters where legal and simple.

- Start with FRED because it has stable series IDs and API documentation. Import into the existing audited observation model, preserving source URL, series ID, as-of, retrieved-at, and method metadata.
- Add adapter diagnostics and dry-run previews before writing observations.
- Treat PBOC and Buffett components as manual-review workflows first unless a reliable official/public structured source is verified.

P1 - Build a personal research notebook/history.

- Persist dashboard brief snapshots, source-gap snapshots, user follow-up questions, and cited evidence IDs.
- Add "read later" or "needs review" state for SEC filings, reports, news, and macro source links.
- Let AI summarize only the notebook's saved evidence plus current platform citations.

P1 - Improve macro/valuation research UX.

- Add indicator detail pages with trend chart, components, methodology, source history, no-data explanation, and related watchlist/reports.
- Add Buffett component calculator UI for market cap, GDP, ratio, as-of, source links, and review notes before importing.
- Add cross-market macro dashboard presets: rates curve, inflation/liquidity, Buffett valuation, risk appetite, and China liquidity.

P2 - Add screener/watchlist intelligence without terminal scope creep.

- Build screener-lite from existing indicators, recommendation signals, fundamentals, news freshness, and macro conditions.
- Add alerts for source updates, indicator thresholds, report generation, stale data, and watchlist changes.
- Show sample size, historical hit-rate windows, data gaps, and non-advice disclaimers with every recommendation/screen result.

P2 - Improve research-grade charting.

- Persist chart layouts and indicator parameters per symbol/watchlist.
- Link chart annotations to notebook notes, reports, and citations.
- Add multi-timeframe and comparison workflows before any scripting or broker features.

## Code Patterns

- Additive backend payload fields are the right contract shape: `collection_note`, `citation_policy`, and `collection_links` are added to source items while evidence and status logic stay separate (`packages/services/information_sources.py:437`, `packages/services/information_sources.py:449`).
- Good FRED pattern: official links are tied to an action and non-citation policy (`packages/services/information_sources.py:112`, `packages/services/information_sources.py:116`, `packages/services/information_sources.py:120`).
- Good macro seed pattern: no default fake observations, and import requires audit source plus method metadata (`packages/services/market_indicators.py:173`, `packages/services/market_indicators.py:394`).
- Good AI pattern: source gaps are prompt context but explicitly not citations (`packages/services/market_dashboard.py:645`, `packages/services/market_dashboard.py:649`).
- Good UI pattern: collection guidance and citation boundary appear near each source item, and external links use safe navigation attributes (`apps/web/app/[locale]/page.tsx:1297`, `apps/web/app/[locale]/page.tsx:1305`, `apps/web/app/[locale]/page.tsx:1320`).
- Good test pattern: one official macro source, one manual valuation source, one future document source, and one frontend external link are covered (`tests/services/test_information_sources_service.py:85`, `tests/services/test_information_sources_service.py:122`, `tests/services/test_information_sources_service.py:152`, `apps/web/app/[locale]/page.test.tsx:606`).

## Related Specs

- `.trellis/spec/backend/assistant-research-citation-contract.md` - keep assistant/dashboard citations tied to known evidence, not source-readiness gaps.
- `.trellis/spec/backend/market-indicator-seed-import-contract.md` - require source and methodology metadata for macro/valuation seed imports.
- `.trellis/spec/frontend/index.md` - homepage/page changes should use existing frontend patterns and localization.
- `.trellis/spec/frontend/component-guidelines.md` - use real links for navigation, existing UI primitives, and visible diagnostics.
- `.trellis/spec/frontend/quality-guidelines.md` - update page tests and i18n strings for visible UI behavior.

## Caveats / Not Found

- This benchmark used public product pages and docs, not paid hands-on access to Bloomberg Terminal, AlphaSense, Koyfin premium features, or broker terminals.
- No runtime app validation or test execution was performed because this was a read-only research task.
- No evidence was found that current code has production FRED/PBOC/SEC adapters, licensed document ingestion, transcript storage, vector search, broker execution, or professional realtime feed entitlement handling. The task PRD explicitly keeps those out of scope (`.trellis/tasks/07-06-07-06-hard-to-find-source-collection-links/prd.md:36`).
- External site capabilities and packaging can change after 2026-07-06. Re-check public docs before converting any benchmark item into implementation requirements.
