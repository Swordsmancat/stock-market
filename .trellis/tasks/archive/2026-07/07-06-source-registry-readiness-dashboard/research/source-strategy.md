# Research: source strategy

- Query: Source strategy for personal investment information aggregation, hard-to-find source collection, and AI summary readiness.
- Scope: mixed
- Date: 2026-07-06

## Findings

### Decision Summary

The source readiness layer should be a source registry and evidence-gap map, not a live ingestion layer. P0 can safely expose static source definitions plus readiness derived from existing local database rows. Official macro sources, PBOC releases, SEC EDGAR, transcripts, news, reports, and user seed files should be categorized by whether they are current_doable, needs_adapter, manual_seed, or future.

The conservative rule is:

- current_doable: registry/readiness display, generated reports, stored news, and any already-seeded `MarketIndicatorObservation` rows.
- needs_adapter: official sources that are technically suitable but have no implemented ingestion/normalization path yet, such as FRED and SEC EDGAR.
- manual_seed: sources where an audited human seed is safer than automation for now, such as China M2 from PBOC monthly releases and Buffett Indicator components.
- future: sources that require licensing, user-provided rights, provider permission, or a separate legal/product decision, such as broad earnings-call transcript corpora and exchange-announcement scraping.

No source should become AI-citable merely because it is listed in the registry. AI can cite only configured evidence that exists locally with source, as-of, and citation metadata.

### Files Found

- `.trellis/tasks/07-06-source-registry-readiness-dashboard/prd.md` - Requires a curated source registry/readiness payload for official macro, China macro, valuation/manual seeds, SEC/announcements/transcripts, existing reports/news/stores, and AI summary safety.
- `.trellis/tasks/07-06-source-registry-readiness-dashboard/design.md` - Defines the slice boundary: no live network calls, readiness from static definitions plus database state, future sources listed as gaps.
- `.trellis/tasks/07-06-source-registry-readiness-dashboard/implement.md` - Plans backend source registry, dashboard payload integration, frontend readiness panel, docs, and tests.
- `.trellis/tasks/07-06-personal-investment-info-ai-summary/prd.md` - Parent direction: personal information aggregation, hard-to-find source collection, source/as-of/method metadata, no unauthorized scraping.
- `.trellis/tasks/07-06-personal-investment-info-ai-summary/design.md` - Source strategy ladder: official APIs, existing providers where terms permit, user-curated seed files, licensed/user-provided documents, link-and-summary workflows.
- `.trellis/tasks/07-06-personal-investment-info-ai-summary/implement.md` - P0/P1/P2 plan that separates macro/valuation, AI brief, official adapters, hard-to-find source collection, and notebooks.
- `.trellis/tasks/07-06-personal-investment-info-ai-summary/research/current-state-and-repositioning.md` - Confirms hard-to-find source collection lacks source type, legal boundary, and freshness policy.
- `.trellis/tasks/07-06-macro-valuation-ai-brief-mvp/research/professional-site-comparison.md` - Recommends personal cockpit positioning, source/method tables, official macro adapters, no unlicensed scraping, and future legal/permissioned document ingestion.
- `.trellis/spec/backend/index.md` - Backend service/router/provider/domain boundaries.
- `.trellis/spec/backend/quality-guidelines.md` - Focused tests and no live provider tests by default.
- `.trellis/spec/backend/database-guidelines.md` - Existing SQLAlchemy session/model/test patterns.
- `.trellis/spec/backend/assistant-research-citation-contract.md` - AI evidence/citation contract: known citation IDs, no fabricated filings/transcripts, no investment advice.
- `.trellis/spec/guides/cross-layer-thinking-guide.md` - Cross-layer payload contract thinking for service-to-API-to-frontend changes.
- `packages/domain/models.py` - Existing macro observations, news articles, sentiment, and generated report evidence stores.
- `packages/services/market_indicators.py` - Macro/valuation definitions and no-data-safe audited observation helper.
- `packages/services/market_dashboard.py` - Dashboard aggregation, deterministic dashboard brief, existing report/news availability citations.
- `packages/services/market_assistant.py` and `packages/ai/market_assistant.py` - Citation-aware assistant and unknown-citation validation.
- `packages/services/news.py` - Existing stored news ingestion/payload shape.
- `packages/services/reports.py` - Generated reports with citations and source summaries.
- `apps/web/app/[locale]/page.tsx` - Frontend already has optional `information_sources` types and readiness panel rendering.
- `apps/web/messages/en.json` and `apps/web/messages/zh.json` - Source readiness panel copy already exists.

### Code Patterns

- Domain storage already supports audited macro observations: `MarketIndicatorObservation` has unique `(indicator_id, as_of)`, value, `source`, and `components_json` fields (`packages/domain/models.py:176`, `packages/domain/models.py:188`, `packages/domain/models.py:190`, `packages/domain/models.py:191`).
- Existing news and report rows can serve as current_doable evidence stores: `NewsArticle` stores `source` and `published_at`, while `GeneratedReport` stores `as_of`, `citations`, and `source_summary` (`packages/domain/models.py:278`, `packages/domain/models.py:285`, `packages/domain/models.py:286`, `packages/domain/models.py:308`, `packages/domain/models.py:314`, `packages/domain/models.py:316`, `packages/domain/models.py:317`).
- The macro indicator registry already includes the intended P0 codes: Buffett CN/HK/US, US 10Y, US 2Y, 10Y-2Y spread, US CPI YoY, US M2 YoY, and CN M2 YoY (`packages/services/market_indicators.py:13`, `packages/services/market_indicators.py:21`).
- The macro service intentionally has no default observations because real values should be added only when source and component values are auditable (`packages/services/market_indicators.py:130`, `packages/services/market_indicators.py:133`).
- Missing indicator definitions and missing observations return `no_data` with a reason rather than fake values (`packages/services/market_indicators.py:234`, `packages/services/market_indicators.py:255`, `packages/services/market_indicators.py:261`).
- Seeded observations preserve source and components for later AI citations and method display (`packages/services/market_indicators.py:168`, `packages/services/market_indicators.py:196`, `packages/services/market_indicators.py:197`, `packages/services/market_indicators.py:273`, `packages/services/market_indicators.py:274`).
- Dashboard research availability already counts local generated reports/news and creates citations for available rows, diagnostics for missing rows (`packages/services/market_dashboard.py:315`, `packages/services/market_dashboard.py:318`, `packages/services/market_dashboard.py:322`, `packages/services/market_dashboard.py:334`, `packages/services/market_dashboard.py:345`, `packages/services/market_dashboard.py:365`, `packages/services/market_dashboard.py:378`).
- Dashboard brief already treats macro missingness, report/news absence, and diagnostics as AI-ready data gaps (`packages/services/market_dashboard.py:431`, `packages/services/market_dashboard.py:433`, `packages/services/market_dashboard.py:437`, `packages/services/market_dashboard.py:455`, `packages/services/market_dashboard.py:460`, `packages/services/market_dashboard.py:485`, `packages/services/market_dashboard.py:490`).
- Market overview currently exposes macro indicators and dashboard brief, but not backend `information_sources` yet (`packages/services/market_dashboard.py:520`, `packages/services/market_dashboard.py:538`, `packages/services/market_dashboard.py:540`).
- Assistant prompts explicitly require known citation IDs and prohibit fabricated unavailable data (`packages/ai/market_assistant.py:117`, `packages/ai/market_assistant.py:136`, `packages/ai/market_assistant.py:137`).
- Unknown LLM citation IDs are detected and downgraded with `CITATION_UNKNOWN_ID` diagnostics (`packages/services/market_assistant.py:523`, `packages/services/market_assistant.py:530`, `packages/services/market_assistant.py:535`).
- Assistant evidence builders already produce structured news and generated-report citation IDs (`packages/services/market_assistant.py:681`, `packages/services/market_assistant.py:682`, `packages/services/market_assistant.py:804`, `packages/services/market_assistant.py:805`).
- Frontend has already reserved `InformationSourceItem`, `InformationSourceGroup`, `InformationSourcesPayload`, and conditional panel rendering for `marketOverviewPayload.information_sources` (`apps/web/app/[locale]/page.tsx:324`, `apps/web/app/[locale]/page.tsx:338`, `apps/web/app/[locale]/page.tsx:344`, `apps/web/app/[locale]/page.tsx:380`, `apps/web/app/[locale]/page.tsx:879`, `apps/web/app/[locale]/page.tsx:1168`).
- No backend source registry helper exists yet: `packages/services/information_sources.py` was not found, and `tests/services/test_information_sources_service.py` was not found.

### Recommended Status Meanings

Use one status enum in the payload and avoid overloaded words:

| Status | Meaning | AI behavior |
|---|---|---|
| `configured` | Local evidence exists for this registry entry and passes the entry's minimal freshness rule, or exists with a visible stale/freshness label. | May be cited if citation metadata is present. If stale, AI may cite only with a stale warning. |
| `needs_adapter` | A legitimate source candidate exists, but no code path imports, normalizes, or stores it. | Not citable. Mention only as a source gap / next action. |
| `needs_manual_seed` | Automation is not ready or not appropriate; user/admin must seed audited value/file metadata with source URL, as-of, method, and rights note. | Not citable until a seed row/file exists. |
| `no_data` | The source/store exists in this platform, but current DB state has no rows for the dashboard scope. | Not citable. Can appear in diagnostics/data gaps. |
| `future` | Source family needs licensing, permission, product design, or a separate adapter/storage model. | Not citable and should not be implied as implemented. |

The requested "current doable / needs_adapter / manual seed / future" split can be represented as a separate route label or derived from status:

- current_doable: `configured` or `no_data` for existing local stores, plus static registry display.
- needs_adapter: `needs_adapter`.
- manual_seed: `needs_manual_seed`.
- future: `future`.

### Source Registry Entries Suggested

| id | Category | Authority / provider | Coverage / series | Initial status | Route | Freshness policy | AI citation/use rule | Next action |
|---|---|---|---|---|---|---|---|---|
| `macro_fred_us_rates` | `macro` | Federal Reserve Bank of St. Louis FRED | `DGS10`, `DGS2`, `T10Y2Y` | `needs_adapter` | needs_adapter | Daily official series. Consider stale if latest observation is older than 3 US business days or source reports no new observation. | Citable only after adapter stores observation value, source URL/series ID, as-of, retrieved_at, and FRED notice/terms metadata. | Add FRED adapter with API key, rate/backoff, series metadata, and terms review. |
| `macro_fred_us_inflation` | `macro` | FRED / underlying official CPI source | `CPIAUCSL` or selected CPI series; compute YoY from official observations. | `needs_adapter` | needs_adapter | Monthly. Consider stale if no current or previous month release within 60 days; preserve revision/vintage metadata where possible. | Citable only after stored observation includes computation method and source series. | Add adapter and explicit YoY transform test. |
| `macro_fred_us_liquidity` | `macro` | FRED / Federal Reserve monetary aggregate series | `M2SL` or selected M2 series; compute YoY. | `needs_adapter` | needs_adapter | Monthly/weekly depending selected series. Store frequency and transformation in components. | Citable only after stored observation exists; AI must state series/frequency caveat. | Select canonical M2 series, add transform/freshness policy. |
| `macro_pbc_cn_m2` | `macro` | People's Bank of China | Monthly financial statistics report; CN M2 YoY and balance. | `needs_manual_seed` | manual_seed | Monthly. Use PBOC publication date and report month; stale if latest as_of is older than 60 days. | Citable only after human-reviewed seed records source URL, report title, as_of month, value, unit, and extraction note. | Add manual seed schema/importer first; only automate later if official structured endpoint is found and permitted. |
| `valuation_buffett_manual_components` | `valuation` | Manual audited mix of official GDP + market-cap/component sources | Buffett Indicator CN/HK/US components. | `needs_manual_seed` | manual_seed | Component-specific. GDP quarterly/annual; market cap daily/monthly depending source. Output is stale if any component exceeds its policy. | Citable only when every component has source URL/ID, as_of, unit, and formula in `components_json`. | Define component table per region before loading values. |
| `documents_sec_edgar_filings` | `documents` | SEC EDGAR / data.sec.gov | Company submissions, 10-K, 10-Q, 8-K, 20-F, 40-F, 6-K, XBRL company facts. | `needs_adapter` | needs_adapter | For watchlist: poll no more than policy allows; filings are event-driven. Store filingDate/acceptanceDatetime and retrieved_at. | Citable only to exact filing/accession/document URL and excerpt. Must include form type, CIK, accession number, filing date. | Add SEC adapter with declared User-Agent, <=10 requests/second, CIK mapping, and local metadata cache. |
| `documents_exchange_announcements` | `documents` | Exchange/company official announcement sites | CN/HK/US exchange announcements where permitted. | `future` | future | Event-driven; source-specific. | Not citable until source terms and adapter are approved. Use link-and-summary or manual seed instead of scraping. | Create separate source/legal review per exchange. |
| `documents_transcripts_permissioned` | `documents` | Licensed provider, company IR, SEC-filed exhibit, or user-provided file | Earnings-call transcripts and presentations. | `future` | future/manual_seed | Event-driven by earnings calendar. Store event date, source, rights note, and retrieval method. | Not citable from scraped transcript sites. Citable only if the transcript is user-provided with rights, company-posted and terms allow use, SEC-filed, or licensed. | Add user-file seed path before provider adapter; avoid unauthorized transcript scraping. |
| `news_stored_articles` | `news` | Existing `NewsArticle` rows from allowed provider/manual ingestion | Symbol-linked stored news metadata, title, URL, summary, sentiment. | `configured` if rows exist, else `no_data` | current_doable | For dashboard narrative, treat news older than 7 days as stale for "what changed"; still usable for history if labeled. | Citable via deterministic news citation ID only when article URL/title/published_at/source exists. Store only content permitted by provider terms. | Keep DB-derived readiness; add provider policy field before broad ingestion. |
| `reports_generated_reports` | `reports` | Existing `GeneratedReport` rows | Stock daily reports and report history. | `configured` if rows exist, else `no_data` | current_doable | Daily report stale after 1 market day for daily cockpit; weekly report stale after 7 days if added later. | Citable via `generated_report:{id}` with report citations/source_summary metadata. | Include latest report count/latest in readiness payload. |
| `manual_seed_user_files` | `manual_seed` | User/admin provided CSV/PDF/markdown/files | Macro seeds, source notes, user research, licensed docs. | `needs_manual_seed` | manual_seed | Source-specific; seed must include as_of and optional expires/stale_after_days. | Citable only if file/source metadata records provenance, rights note, as_of, retrieved_at/imported_at, and excerpt boundaries. | Add importer/schema and "user supplied, rights asserted" metadata. |
| `watchlist_platform_store` | `reports` | Existing watchlist/local platform state | Followed symbols used to scope reports/news/source readiness. | `configured` if watchlist items exist, else `no_data` | current_doable | Current dashboard scope, not an external source. | Not a factual market citation by itself; use only to explain scope. | Use as readiness scope input. |

### Freshness Policy

P0 should store freshness as readable policy text in the static registry and compute only simple readiness fields from DB:

- `evidence_count`: count of local records mapped to the source.
- `latest_as_of`: latest source observation/report/news/filing date, not necessarily retrieval date.
- `latest_retrieved_at` or `latest_created_at`: when the platform last fetched/imported/generated the evidence, if available.
- `freshness_status`: optional computed status such as `fresh`, `stale`, `no_data`, `unknown`, or `future`; do not overbuild this if the PRD only asks for source readiness status.

Recommended thresholds:

- Daily rates/market source: stale after 3 business days without a newer official/source observation.
- Monthly macro source: stale after 60 calendar days from the observation month unless the source's release calendar says otherwise.
- PBOC CN M2: stale after 60 days from as_of month; publication date should be stored separately because the report can be published mid-month.
- SEC filings: event-driven; for watchlist monitoring, stale if no check occurred in the last business day once adapter exists. A filing itself is historical evidence and does not expire, but "latest filing coverage" can be stale.
- News: for daily dashboard narrative, stale after 7 days; older rows can remain historical evidence if labeled.
- Generated reports: daily stale after 1 market day; weekly stale after 7 days if/when weekly reports exist.
- User seed files: seed must carry explicit `as_of` and either a source-specific stale rule or `manual_review_required`.

Do not run live network calls in `/dashboard/market-overview` for freshness. The dashboard should only read database state and static source definitions in this slice.

### AI Citation / Use Rules

- AI prompts may list only citation IDs backed by local evidence. Registry gaps must not be listed as citations.
- A source with `needs_adapter`, `needs_manual_seed`, `no_data`, or `future` can be mentioned only under "data gaps", "missing sources", or "next collection action".
- AI cannot infer an official macro value from a source definition. A FRED/PBOC entry without an observation row remains a gap.
- AI cannot cite filings, transcripts, announcements, or research reports until there is a local evidence item with URL/source ID, as_of/event date, retrieved/imported timestamp, and excerpt/metadata.
- AI should cite generated reports only with their own report citation ID and should preserve underlying report citations in metadata; do not collapse a generated report into proof of the underlying facts unless those underlying citations are present.
- AI should cite news with title, URL, source, published_at, and provider. If provider terms allow only links/headlines, store/link metadata and short permitted excerpts rather than full-text content.
- AI must keep no-investment-advice boundaries: research hypotheses and watchpoints only, no buy/sell/hold, target price, position sizing, or execution instruction.
- Unknown inline citation IDs from LLM output must remain invalid and should trigger deterministic fallback/diagnostics as in the current assistant contract.

### P0 / P1 / P2 Route

P0, source readiness dashboard:

- Add a static source registry service and readiness builder.
- Read only existing DB stores: `MarketIndicatorObservation`, `GeneratedReport`, `NewsArticle`, and watchlist/followed scope if needed.
- Include official macro, PBOC, SEC, transcripts, reports, news, and manual seed entries as gaps/action items where not implemented.
- Render gaps as action-oriented status, not errors.
- Do not add live network calls, scrapers, or broad document ingestion.
- Keep frontend/API payload additive.

P1, official and manual-source ingestion:

- Add FRED adapter only after API key/config, source-series selection, rate/backoff, required attribution/notice, and third-party-series rights review.
- Add manual seed import for PBOC CN M2 and Buffett components before automation.
- Add SEC EDGAR adapter for watchlist filings metadata and selected filing documents, respecting declared User-Agent and fair-access request limits.
- Add user seed file ingestion for legally usable PDFs/markdown/CSV/source notes with rights/provenance metadata.
- Extend dashboard AI brief to use the same citation validation contract against source registry evidence.

P2, hard-to-find document intelligence:

- Add permissioned transcript workflows: user-uploaded, company IR/SEC-filed, or licensed provider only.
- Add exchange-announcement adapters only after per-source terms review.
- Add document/excerpt store, vector retrieval, source-quality scoring, and personal research notebook.
- Add scheduled freshness checks and source-health history.
- Keep professional paid research/news feeds out of scope unless licensed.

### External References

Checked on 2026-07-06.

- FRED API docs: https://fred.stlouisfed.org/docs/api/fred/
- FRED `series/observations` docs: https://fred.stlouisfed.org/docs/api/fred/series_observations.html
- FRED API Terms of Use: https://fred.stlouisfed.org/docs/api/terms_of_use.html
- FRED DGS10: https://fred.stlouisfed.org/series/DGS10
- FRED DGS2: https://fred.stlouisfed.org/series/DGS2
- FRED T10Y2Y: https://fred.stlouisfed.org/series/T10Y2Y
- FRED CPIAUCSL: https://fred.stlouisfed.org/series/CPIAUCSL
- FRED M2SL: https://fred.stlouisfed.org/series/M2SL
- PBOC Survey and Statistics Department index: https://www.pbc.gov.cn/diaochatongjisi/116219/index.html
- PBOC monthly financial statistics reports should be captured from the official PBOC statistics/communications pages during manual seeding; search results often surface third-party reprints, so do not hard-code an unverified report URL.
- SEC EDGAR APIs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- SEC Accessing EDGAR Data / fair access: https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
- Yahoo Terms of Service: https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html
- Seeking Alpha Terms of Use, as an example transcript/content provider with restrictive content and automated retrieval terms: https://about.seekingalpha.com/terms

Key external-source implications:

- FRED provides official API access to series observations, but its API terms make users responsible for third-party series restrictions and required notices. Treat FRED as `needs_adapter` plus terms review, not as already configured.
- PBOC publishes monthly financial statistics reports with CN M2 values, but this project should start with manual-reviewed seeds that capture the exact official PBOC URL at seed time unless an official structured endpoint and allowed automation path are confirmed.
- SEC EDGAR is a strong `needs_adapter` source: data.sec.gov APIs are unauthenticated and provide submissions/XBRL JSON, but automated access must follow SEC fair-access rules, declared User-Agent, and efficient request behavior.
- Yahoo-style/news sources and transcript providers often restrict automated collection or reuse. Existing stored news can be used if already lawfully ingested, but broad scraping or full-text transcript ingestion should not be recommended without permission/license/user rights.

### Related Specs

- `.trellis/spec/backend/index.md` - Use service-layer helper and additive dashboard payload; keep routers thin.
- `.trellis/spec/backend/quality-guidelines.md` - Add focused service/API tests; avoid tests requiring live providers by default.
- `.trellis/spec/backend/database-guidelines.md` - Read database state through explicit sessions and existing ORM models.
- `.trellis/spec/backend/assistant-research-citation-contract.md` - Treat missing filings/transcripts as diagnostics/gaps, validate citation IDs, and preserve no-investment-advice safety.
- `.trellis/spec/guides/cross-layer-thinking-guide.md` - Source readiness payload is a cross-layer contract; backend shape and frontend optional rendering must stay aligned.

## Caveats / Not Found

- This research did not edit code, README, docs, tests, or task metadata.
- `packages/services/information_sources.py` and `tests/services/test_information_sources_service.py` were not present at research time.
- No production FRED, PBOC, SEC EDGAR, exchange-announcement, transcript, or user seed-file adapter was found.
- Frontend readiness panel scaffolding appears to exist, but backend payload wiring was not found.
- External source terms can change. FRED, Yahoo, SEC, PBOC, and transcript provider policies should be reviewed again before implementing adapters or storing source content.
- The exact PBOC monthly report URL was not verified in this turn; use the official PBOC statistics index and capture the source URL manually when seeding CN M2.
- This is source-strategy research, not legal advice. Where source rights are ambiguous, use manual seed/link-only/permissioned workflows and avoid unauthorized scraping.
