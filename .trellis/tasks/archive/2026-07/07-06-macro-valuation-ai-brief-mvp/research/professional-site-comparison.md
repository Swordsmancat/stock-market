# Research: professional-site-comparison

- Query: Compare professional finance/investment information sites against this personal investment information + macro valuation + AI brief MVP; identify current positioning, covered MVP capabilities, gaps, P0/P1/P2 optimization route, and features to avoid.
- Scope: mixed
- Date: 2026-07-06

## Findings

### Current Positioning Conclusion

The right product position is a personal investment information cockpit, not a professional trading terminal. The site should aggregate scattered market, macro, valuation, watchlist, report, and news context, then use source-aware AI/deterministic summaries to explain:

- what changed.
- why it matters.
- what to watch next.
- what evidence supports the summary.
- which data is missing or stale.

The strongest benchmark is not Bloomberg/TradingView parity. The useful benchmark is source transparency, macro context density, personal workflow fit, and safe AI synthesis. Professional sites should inspire data organization and evidence UX, while this MVP should deliberately avoid execution, entitlement-heavy real-time feeds, Level-2/order-flow, and broad professional screener/backtest parity.

### Files Found

- `.trellis/tasks/07-06-macro-valuation-ai-brief-mvp/prd.md` - P0 requirements for macro/valuation indicator registry, auditable observations, dashboard daily brief, AI-ready contract, frontend positioning, and docs.
- `.trellis/tasks/07-06-macro-valuation-ai-brief-mvp/design.md` - Technical design for indicator definitions, no-data behavior, dashboard brief payload, UI, docs, compatibility, and rollback.
- `.trellis/tasks/07-06-macro-valuation-ai-brief-mvp/implement.md` - Implementation checklist covering backend registry, daily brief, API payload, frontend dashboard, docs, and validation.
- `.trellis/tasks/07-06-macro-valuation-ai-brief-mvp/research/` - Child task research directory existed but had no files before this research.
- `.trellis/tasks/07-06-personal-investment-info-ai-summary/prd.md` - Parent positioning: personal information aggregation, macro/valuation collection, hard-to-find source gathering, AI summary/recommendation, no professional terminal competition.
- `.trellis/tasks/07-06-personal-investment-info-ai-summary/research/current-state-and-repositioning.md` - Prior current-state research recommending P0 macro/valuation definitions, audited seed/import, deterministic daily brief, and docs repositioning.
- `.trellis/spec/backend/index.md` - Backend layer index: FastAPI routers, service layer, provider boundary, SQLAlchemy models, focused pytest.
- `.trellis/spec/backend/quality-guidelines.md` - Backend quality pattern: thin routers, service tests, explicit sessions, no live provider tests by default.
- `.trellis/spec/backend/assistant-research-citation-contract.md` - AI/citation contract: deterministic citation IDs, diagnostics for missing evidence, no direct buy/sell/hold advice.
- `.trellis/spec/frontend/index.md` - Frontend layer index: Next.js App Router, server pages, route proxies, next-intl, tests.
- `.trellis/spec/frontend/component-guidelines.md` - Frontend component conventions: server data pages, existing UI primitives, EmptyState/ErrorState.
- `.trellis/spec/frontend/quality-guidelines.md` - Frontend quality expectations: update translations together, focused visible-behavior tests.
- `packages/domain/models.py` - Existing `MarketIndicator` and `MarketIndicatorObservation` persistence model.
- `packages/services/market_indicators.py` - Macro/valuation indicator definitions, no-data payloads, and audited observation upsert helper.
- `packages/services/market_dashboard.py` - Dashboard aggregation, macro indicators, and deterministic dashboard brief.
- `apps/api/routers/dashboard.py` - `/dashboard/market-overview` endpoint exposing the aggregated payload.
- `apps/web/app/[locale]/page.tsx` - Homepage/dashboard rendering of AI research brief, macro indicators, source/as-of/no-data metadata.
- `apps/web/messages/en.json` and `apps/web/messages/zh.json` - Dashboard copy for AI research brief and macro/valuation indicators.
- `tests/services/test_market_indicators_service.py` - Service tests for indicator definitions, no-data state, audited observation metadata.
- `tests/services/test_market_dashboard_service.py` - Service tests for macro indicator payload and dashboard brief degraded behavior.
- `tests/api/test_dashboard_api.py` - API test for macro/valuation and dashboard brief fields.
- `apps/web/app/[locale]/page.test.tsx` - Page test for AI brief and macro indicator rendering.
- `README.md` and `docs/manual/user-guide.md` - Documentation still contains professional-terminal comparison language that should be reframed.

### Code Patterns

- The domain already has first-class macro/valuation storage: `MarketIndicator` stores code/name/category/region/unit/display order, and `MarketIndicatorObservation` stores `as_of`, numeric value, source, and `components_json` for methodology/source metadata (`packages/domain/models.py:152`, `packages/domain/models.py:176`, `packages/domain/models.py:188`, `packages/domain/models.py:190`, `packages/domain/models.py:191`).
- The indicator registry now defines a curated P0 macro set: Buffett Indicator CN/HK/US, US 10Y, US 2Y, US 10Y-2Y spread, US CPI YoY, US M2 YoY, and China M2 YoY (`packages/services/market_indicators.py:12`, `packages/services/market_indicators.py:46`).
- Default observations are intentionally empty, which preserves the no-fabrication rule until audited observations are loaded (`packages/services/market_indicators.py:133`).
- Missing indicator definitions and missing observations return explicit `no_data`, with an explanation instead of zero or fabricated values (`packages/services/market_indicators.py:221`, `packages/services/market_indicators.py:261`).
- The broader macro payload helper seeds definitions and returns the curated codes in order (`packages/services/market_indicators.py:285`).
- Dashboard brief evidence IDs are deterministic and source-specific (`market_indicator:{code}:{as_of}`), matching the assistant citation pattern (`packages/services/market_dashboard.py:256`).
- The deterministic brief is built from followed-instrument freshness and macro indicator availability, then returns sections for `what_changed`, `why_it_matters`, `what_to_watch_next`, and `data_gaps` (`packages/services/market_dashboard.py:277`, `packages/services/market_dashboard.py:342`).
- The brief includes citations for available indicators, diagnostics for missing indicators, and safety flags for no investment advice, no buy/sell/hold, and no fabricated macro data (`packages/services/market_dashboard.py:347`, `packages/services/market_dashboard.py:350`).
- The market overview payload exposes both `macro_indicators` and backward-compatible `valuation_indicators`, plus `dashboard_brief` (`packages/services/market_dashboard.py:396`, `packages/services/market_dashboard.py:397`, `packages/services/market_dashboard.py:398`).
- The API endpoint is a thin router delegating to the dashboard service (`apps/api/routers/dashboard.py:10`, `apps/api/routers/dashboard.py:15`).
- Frontend payload types include macro/valuation items with status, value, unit, as-of, source, components, and no-data reason, plus dashboard brief sections/citations/diagnostics/safety (`apps/web/app/[locale]/page.tsx:264`, `apps/web/app/[locale]/page.tsx:284`, `apps/web/app/[locale]/page.tsx:327`, `apps/web/app/[locale]/page.tsx:333`).
- The homepage groups indicators by category and renders the dashboard brief near the top (`apps/web/app/[locale]/page.tsx:692`, `apps/web/app/[locale]/page.tsx:1057`).
- The homepage renders brief citations/diagnostics and macro indicator source/as-of/no-data details near the value (`apps/web/app/[locale]/page.tsx:1084`, `apps/web/app/[locale]/page.tsx:1096`, `apps/web/app/[locale]/page.tsx:1244`, `apps/web/app/[locale]/page.tsx:1270`, `apps/web/app/[locale]/page.tsx:1273`).
- English and Chinese copy now frame the module as "AI research brief" and "Macro and valuation indicators" with auditable source/as-of metadata (`apps/web/messages/en.json:84`, `apps/web/messages/en.json:88`, `apps/web/messages/zh.json:91`, `apps/web/messages/zh.json:95`).
- Tests cover no-data definitions, audited observation metadata including a FRED DGS10-style seed, macro code coverage, dashboard brief degraded state, API payload fields, and frontend rendering (`tests/services/test_market_indicators_service.py:84`, `tests/services/test_market_indicators_service.py:105`, `tests/services/test_market_dashboard_service.py:77`, `tests/services/test_market_dashboard_service.py:92`, `tests/api/test_dashboard_api.py:42`, `apps/web/app/[locale]/page.test.tsx:501`, `apps/web/app/[locale]/page.test.tsx:520`).
- Documentation still over-indexes on professional terminal comparison: README mentions "Professional dashboard surface" and terminal gaps (`README.md:96`), while the user guide compares against TradingView/Bloomberg/Koyfin/AlphaSense and lists terminal-style gaps (`docs/manual/user-guide.md:196`, `docs/manual/user-guide.md:201`, `docs/manual/user-guide.md:205`, `docs/manual/user-guide.md:230`).

### Common Professional-Site Capabilities

| Platform/source | Common public capability pattern | What this MVP should borrow | What this MVP should not chase |
|---|---|---|---|
| Bloomberg Terminal | Real-time multi-asset data, market news, analytics, charts, collaboration, portfolio analytics, execution/order workflows, and AI research over structured data plus documents. | Evidence-dense brief UX, citation/source rigor, cross-source context, analyst-style summaries. | Execution/order management, entitlement-heavy real-time feeds, multi-asset institutional breadth, terminal command parity. |
| TradingView | Supercharts, indicators, drawing tools, alerts, screeners, calendars, social/trader workflow, broker integrations. | Clean chart/watchlist ergonomics, economic-calendar inspiration, visible event context. | Pine/script platform, social trading network, broker trading, realtime trader scanner parity. |
| Koyfin | Custom dashboards, macro dashboards, financial analytics, charts, equity research, news, screeners. | Macro dashboard organization, flexible curated views, cross-asset context for personal research. | Institutional terminal clone, broad paid data coverage, full professional workstation. |
| MacroMicro | Global macro datasets, cycle/indicator views, macro charts, investment-cycle explanations, macro-first discovery. | Macro-first hierarchy, "why this chart matters" explanations, curated economic cycle watchpoints. | Rebuilding a full global macro database or generic macro content site. |
| Yahoo Finance | Quotes, news, portfolios/watchlists, screeners, charts, mobile alerts, broad accessible market context. | Personal watchlist/portfolio aggregation and accessible daily monitoring. | Generic quote/news portal clone or broad retail screener clone. |
| Finviz | Screener, maps/heatmaps, groups, portfolio, news, futures/forex/crypto pages, premium real-time/alerts. | Later: compact heatmap/screener-inspired overview for research leads. | Real-time trader scanning, exhaustive factor filters, premium alert/feed parity. |
| FRED / official macro sources | Official macro time series, API observations, release/source metadata, downloadable series. | Auditable source adapters for rates, CPI, M2, spreads, and release freshness. | Treating official macro APIs as a polished frontend product; they are source pipes, not the UI benchmark. |
| AlphaSense / document intelligence products | AI search/summarization over filings, transcripts, news, broker/expert research, and large document corpora. | P1/P2 direction for legal/permissioned document ingestion and source-backed AI summaries. | Paid corpus parity, broker research entitlements, large-scale unlicensed scraping. |

### Current MVP Covered Capabilities

- Curated macro/valuation registry exists for the P0 indicator set.
- The no-data contract is correct: definitions can be visible without pretending that live or audited observations exist.
- The observation model can store auditable source, as-of date, and components/method metadata.
- The dashboard payload includes macro indicators while preserving the old `valuation_indicators` key for compatibility.
- The deterministic dashboard brief exists and has the right research-safe section structure.
- The brief emits evidence citations, diagnostics, and safety flags instead of investment instructions.
- The homepage renders the AI research brief and macro/valuation indicators with status, source/as-of, and no-data reason near the values.
- Backend, API, and frontend tests cover the main payload and rendering contracts.
- English/Chinese frontend copy already points users toward AI research summary and macro/valuation watchpoints.

### Requirement Gaps

- No official source adapter/import flow exists yet for FRED/PBOC/other macro data. The current default state is intentionally definition-only.
- The current brief uses macro indicator and followed-instrument freshness, but it does not yet ingest latest report/news availability as structured backend evidence despite the PRD requiring report/news availability in the brief.
- CPI YoY, M2 YoY, China M2 YoY, and Buffett Indicator values need explicit methodology/source maps before any values are populated.
- Buffett Indicator methodology is the highest-risk source problem because market cap, GDP, region definition, unit normalization, revision policy, and update cadence must be auditable.
- No persistence exists for daily/weekly brief history.
- No P1 citation-aware LLM dashboard brief exists yet; the current brief is deterministic, which is correct for P0 but limited.
- No source-status page or operator workflow exists for "which macro series is configured, last retrieved, last audited, and why missing."
- README/user guide still carry professional-terminal comparison language and should be rewritten around personal information aggregation and AI research summaries.
- No personal notebook/user notes or user-provided document workflow exists.
- No legal/source-policy registry exists for hard-to-find information collection.

### MVP Must Satisfy

P0 should be considered good enough when it:

- Presents the product as personal investment information aggregation + AI interpretation.
- Shows macro/valuation definitions even when observations are missing.
- Uses `no_data` and explicit reasons for missing data.
- Shows source/as-of/method metadata next to any value.
- Produces a deterministic daily brief with the four required sections.
- Treats AI/recommendations as research hypotheses, not trading instructions.
- Does not claim live macro feeds unless a real adapter/import path and freshness policy exist.
- Reframes docs away from terminal competition.

### P0/P1/P2 Optimization Route

P0 closeout / hardening:

- Rewrite README and user guide around personal cockpit, macro/valuation collection, AI brief, source/freshness, and no-investment-advice boundaries.
- Add a source-method table for each P0 indicator: source URL, series ID, formula, unit, frequency, freshness policy, revision policy, and expected no-data reason.
- Extend deterministic dashboard brief inputs to include latest report/news availability as explicit evidence/diagnostics.
- Keep all macro observations empty unless source and component metadata are audited.
- Add a small "source readiness" operator view or diagnostic output so missing macro data is actionable.

P1:

- Add official-source adapters/importers, starting with FRED for US rates/CPI/M2 and a carefully scoped PBOC/manual-import path for China M2.
- Add citation-aware LLM dashboard brief using the existing assistant citation validation pattern.
- Persist daily/weekly briefs so the user can review changes over time.
- Add watchlist-level event digest: price moves, reports, news, macro changes, and missing data in one summary.
- Add user-provided notes/files as evidence inputs with explicit source labels.

P2:

- Add legal/permissioned document ingestion for SEC filings, transcripts, announcements, and user-uploaded research.
- Add personal research notebook workflow with saved AI follow-ups and citations.
- Add macro/valuation alerts and indicator threshold watches.
- Add richer portfolio/risk analytics as context for summaries, not as broker/execution tooling.
- Consider lightweight screener/heatmap views only as research-lead generators.

### Features Not Recommended

- Broker integration, order placement, automatic trading, or execution workflow.
- Low-latency real-time feed parity, Level-2/order book, tick/quote replay, order-flow heatmaps, or professional entitlement management.
- TradingView-style scripting/social trading/community publishing.
- Bloomberg/Koyfin-style broad institutional terminal clone.
- Finviz/Yahoo-style exhaustive retail stock screener clone as a near-term goal.
- Full strategy backtesting engine or portfolio optimizer before source reliability and AI evidence are mature.
- AI output that says buy/sell/hold, target price, position sizing, or guaranteed return.
- Unlicensed scraping of premium research, transcripts, broker reports, or sites with restrictive terms.
- Showing mock/demo/provider-derived data without visible source, freshness, and degraded/no-data labels.

### External References / Sources

Checked on 2026-07-06.

- Bloomberg Terminal official product page: https://professional.bloomberg.com/products/bloomberg-terminal/
- Bloomberg Terminal AI / ASKB page: https://professional.bloomberg.com/products/bloomberg-terminal/ai/
- Bloomberg Terminal charts page: https://professional.bloomberg.com/products/bloomberg-terminal/charts/
- TradingView features page: https://www.tradingview.com/features/
- TradingView Supercharts help: https://www.tradingview.com/support/solutions/43000746464-getting-started-with-supercharts/
- TradingView Economic Calendar: https://www.tradingview.com/economic-calendar/
- TradingView calendar help: https://www.tradingview.com/support/solutions/43000707391-tradingview-calendar-key-economic-and-corporate-events/
- Koyfin homepage / macro dashboards: https://www.koyfin.com/
- Koyfin equity research page: https://www.koyfin.com/for-investors/equity-research/
- Koyfin market dashboards: https://www.koyfin.com/features/market-dashboards/
- MacroMicro homepage: https://en.macromicro.me/
- MacroMicro global macro report: https://en.macromicro.me/macro
- Yahoo Finance homepage: https://finance.yahoo.com/
- Yahoo Finance portfolios/watchlists: https://finance.yahoo.com/portfolios/
- Yahoo Finance screener: https://finance.yahoo.com/research-hub/screener/
- Yahoo Finance mobile/about page: https://finance.yahoo.com/about/mobile/
- Finviz homepage: https://finviz.com/
- Finviz screener help: https://finviz.com/help/screener
- Finviz Elite page: https://finviz.com/elite
- FRED main site: https://fred.stlouisfed.org/
- FRED API Version 2 docs: https://fred.stlouisfed.org/docs/api/fred/
- FRED series observations docs: https://fred.stlouisfed.org/docs/api/fred/series_observations.html
- FRED DGS10: https://fred.stlouisfed.org/series/DGS10
- FRED DGS2: https://fred.stlouisfed.org/series/DGS2
- FRED T10Y2Y: https://fred.stlouisfed.org/series/T10Y2Y
- FRED CPIAUCSL: https://fred.stlouisfed.org/series/CPIAUCSL
- FRED M2SL: https://fred.stlouisfed.org/series/M2SL
- People's Bank of China English homepage with headline macro indicators: https://www.pbc.gov.cn/en/3688006/index.html
- SEC EDGAR APIs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- AlphaSense homepage: https://www.alpha-sense.com/
- AlphaSense "What is AlphaSense" product article: https://www.alpha-sense.com/resources/product-articles/what-is-alphasense/
- AlphaSense financial research platform: https://www.alpha-sense.com/solutions/financial-research-platform/

### Related Specs

- `.trellis/spec/backend/index.md` - confirms service/router/domain/provider boundaries for backend changes.
- `.trellis/spec/backend/quality-guidelines.md` - supports focused service/API tests and avoiding live provider tests by default.
- `.trellis/spec/backend/assistant-research-citation-contract.md` - directly relevant to dashboard AI brief: known citation IDs, diagnostics for missing evidence, deterministic fallback, no direct trading advice.
- `.trellis/spec/frontend/index.md` - confirms Next.js App Router and i18n message conventions.
- `.trellis/spec/frontend/component-guidelines.md` - supports rendering via existing UI primitives and visible empty/error state patterns.
- `.trellis/spec/frontend/quality-guidelines.md` - supports updating EN/ZH strings together and testing visible rendering.

## Caveats / Not Found

- Professional platform capabilities were checked from public pages and search-result-accessible content only; logged-in, paid, region-specific, and entitlement-specific behavior was not verified.
- Exact paid feature boundaries for Bloomberg, Koyfin, Yahoo Finance, TradingView, MacroMicro, and Finviz can change; this research should be used for product direction, not vendor procurement.
- Current code appears to contain the core P0 implementation, but no validation commands were run in this research turn.
- Child-task research directory had no existing research file before this document. The parent task had a short current-state/repositioning research file and was consulted.
- FRED/PBOC source pages confirm viable source candidates, but this research did not implement or verify adapters, API keys, rate limits, licensing, or long-term archival policy.
- China M2 source access needs extra care: PBOC displays headline values publicly, but production ingestion may require a specific official statistics endpoint, manual curation, or an approved secondary source.
