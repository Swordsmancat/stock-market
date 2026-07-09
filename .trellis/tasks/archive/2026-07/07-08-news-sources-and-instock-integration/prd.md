# News sources and InStock integration

## Goal

Add a configurable, citation-safe news/search provider layer for financial news and public sentiment, then plan a staged integration of `myhhub/stock` (InStock) capabilities, including high-risk automatic-trading capability, without weakening this product's evidence, safety, and audit boundaries.

The first principle: external search results, social chatter, source-readiness links, and scraped pages are collection inputs. They become AI-citable evidence only after normalized storage with source URL, publisher/source, published time or retrieved time, and no-fabrication diagnostics.

## User Value

- Users can configure paid/free search providers once and reuse them for A-share, US, and HK news discovery.
- The platform can broaden news coverage beyond yfinance/AkShare while preserving transparent source, freshness, and fallback status.
- Social sentiment can be captured as a separate signal class instead of being mixed into verified news.
- InStock capabilities can improve quantitative analysis coverage, but only through reviewed, testable slices that match this project architecture.
- Automatic-trading capability can be explored deliberately with explicit risk controls instead of being copied in as an opaque broker-execution module.

## Confirmed Facts

- Current local news storage exists through `NewsArticle` and `SentimentSignal` in `packages/domain/models.py`.
- `packages/services/news.py` currently supports `yfinance`, `akshare`, a `tushare` placeholder, and `mock_news`; it dedupes by title and URL and stores keyword sentiment.
- `apps/api/routers/news.py` exposes only mock ingest plus database read endpoints today.
- `packages/services/information_sources.py` already has a `stored_news` readiness item and says local stored news can be cited only after it exists with URL and publication metadata.
- Settings are stored in `data/platform_settings.json`; both backend and web settings stores preserve sensitive values and expose only configured flags for secrets.
- The current Python stack includes `pandas`, `yfinance`, `httpx`, FastAPI, SQLAlchemy, Celery, and Redis; it does not include TA-Lib, MySQL-specific InStock dependencies, or trading dependencies.
- The web app is Next.js App Router under `apps/web`, with settings mutations using Server Actions and localized copy in `apps/web/messages/en.json` and `apps/web/messages/zh.json`.
- Anspire AI Search docs show a Bearer-auth GET endpoint at `https://plugin.anspire.cn/api/ntsearch/search`, with query, top_k, site/time filters, search_type, and region_mode, returning web results with title, content, URL, score, and date.
- SerpAPI Baidu docs require `q`, `engine=baidu`, and `api_key`; the Baidu result schema includes news and social/media result families.
- Tavily Search exposes a search endpoint and SDK; responses include answer, results with title/url/content/score, request id, and usage.
- Bocha markets a Web Search API with news, image, video, encyclopedia, academic, and other sources; precise API contract still needs official-doc follow-up because linked docs are hosted off the landing page.
- Brave Search API exposes `https://api.search.brave.com/res/v1/web/search` with `X-Subscription-Token`; the docs explicitly call out freshness, news use cases, and storage-right constraints.
- MiniMax search is currently documented primarily as Token Plan MCP / CLI `web_search` / `mmx search` capability, not yet confirmed as a simple server-side REST adapter for this app.
- `myhhub/stock` was inspected at HEAD `b6e0ca2268cfbadd02f5ed052159c187b6670231`. It is Apache-2.0 and includes integrated stock selection, daily stock/ETF data jobs, TA-Lib indicators, K-line pattern recognition, CYQ/chip distribution, strategies, backtest stats, watchlist, batch jobs, proxy/cookie support, MySQL/Tornado web UI, and automatic trading examples.
- User confirmed on 2026-07-08 that "integrate all functionality" includes automatic trading.
- User confirmed on 2026-07-08 that the first implementation slice should be news-source configuration, 1-2 search adapters, and degraded diagnostics.
- User confirmed automatic trading can wait, and non-trading InStock capabilities are more important in the near term.
- User confirmed on 2026-07-08 that the first adapter MVP should implement Anspire AI Search and SerpAPI Baidu.

## Requirements

### R1. News Provider Configuration

- Add a provider registry for Anspire AI Search, SerpAPI Baidu, Tavily, Bocha Search, Brave Search, MiniMax search, existing yfinance/AkShare/Tushare, and mock fallback.
- Implement Anspire AI Search and SerpAPI Baidu as the first live-search adapters; keep Tavily, Bocha, Brave, MiniMax, yfinance, AkShare, Tushare, and mock represented in the registry.
- Store provider settings in the existing platform-settings pattern unless implementation proves backend-only env config is safer for a specific secret.
- Per provider, track enabled state, priority/order, API key configured flag, optional base URL, supported markets/regions, supported result kinds, timeout, max results, and a non-sensitive readiness note.
- Do not expose raw API keys/tokens through public settings responses or frontend tests.

### R2. Unified News Search Adapter Contract

- Introduce a normalized adapter result shape for candidate articles:
  - symbol/query, title, URL, source/publisher, summary/snippet, published_at if known, retrieved_at, provider, language/region if known, relevance score if known, result kind, and raw diagnostic metadata.
- Normalize provider-specific results into this shape before persistence.
- Keep raw provider payloads out of user-visible UI unless they are sanitized and useful for diagnostics.
- Treat search results as collection candidates until stored as `NewsArticle` or another reviewed evidence model.

### R3. Ingestion, Deduplication, Sentiment, And Citation Boundary

- Reuse existing `NewsArticle` / `SentimentSignal` where possible.
- Extend schema only if required to preserve provider diagnostics, result kind, retrieved_at, or social-signal metadata without overloading existing columns.
- Deduplicate across providers by normalized URL/title, preserving first-seen and source metadata.
- Keep deterministic sentiment fallback available when no LLM is configured.
- If LLM-assisted summarization or sentiment is added, it must fail closed to deterministic fallback and record diagnostics.

### R4. Social Sentiment

- Model social/public-opinion collection separately from verified news.
- Social sources must use official APIs, licensed provider results, or user-reviewed notes; no hidden scraping or cookie-based social crawling in the MVP.
- Social sentiment must show lower evidence strength than verified news and must not become AI-citable market fact without review.

### R5. Fallback And Degraded Rules

- Provider execution should follow configured priority.
- Missing key, disabled provider, timeout, rate limit, empty response, invalid response, and provider error should all produce explicit diagnostics.
- If one provider fails, continue to the next configured provider when allowed by the request.
- If all live providers fail, fall back to existing stored database news before returning an empty no-data result.
- Never fabricate titles, publication times, prices, movement, or sentiment because a provider failed.

### R6. Settings And UI Experience

- Add a settings surface for news/search providers with scan-friendly rows/cards, enabled toggles, priority/order, configured flags, and provider status.
- Use localized text and existing UI primitives.
- Keep controls compact and operational; avoid a marketing-style provider gallery.
- Provide a low-risk test/readiness action only if it can avoid consuming paid quota in automated tests.

### R7. InStock Integration Strategy

- Treat `myhhub/stock` as an input for staged integration, not a drop-in replacement.
- Prefer porting or adapting small pure analysis modules into this project's service/provider boundaries with attribution and tests.
- Candidate first slices:
  - technical indicators that overlap current analysis gaps,
  - K-line pattern recognition,
  - strategy screening as explainable research signals,
  - backtest statistics for research validation.
- Do not import InStock's MySQL/Tornado web UI, scheduler, proxy/cookie crawling setup, or trading client as-is. Each must be redesigned against this app's FastAPI/Celery/Next.js boundaries.

### R8. Automatic Trading Safety Boundary

- Automatic trading is in the overall scope, but it must be a separate high-risk child track with its own PRD, design, and implementation plan.
- The first auto-trading slice must be simulation/paper-trading only unless the user separately approves live execution after reviewing the safety design.
- Required safety capabilities before any live broker order:
  - credential storage plan that never exposes broker secrets in public settings or logs;
  - broker adapter contract with explicit supported broker/client versions;
  - order intent, dry-run, approval, execution, cancellation, and reconciliation states;
  - immutable audit log for generated signal, user approval, submitted order, broker response, and errors;
  - risk limits for symbol allowlist, max order value, max daily value, max position exposure, and kill switch;
  - market-hours and trading-calendar validation;
  - idempotency keys to prevent duplicate orders on retries;
  - deterministic tests and broker-mocked integration tests;
  - UI language that distinguishes research signal, suggested order intent, paper order, and live order.
- InStock's automatic-trading examples may inform adapter shape, but live execution must not be copied without a new safety review.

### R9. Tests And Safety

- Add backend service tests for provider normalization, fallback sequencing, dedupe, and diagnostics.
- Add API tests for settings and news ingestion endpoints.
- Add frontend tests for settings UI behavior if web settings are changed.
- Paid provider calls must be mocked in tests.
- Documentation must explain provider keys, citation boundaries, storage/licensing caveats, and automatic-trading risk controls.

## Acceptance Criteria

- [ ] A PRD, design, and implementation plan exist before coding starts.
- [ ] News provider settings can represent the requested providers without exposing secrets publicly.
- [ ] At least one live-search adapter slice can normalize results into the local news ingestion path with tests and no network calls in test runs.
- [ ] Fallback diagnostics distinguish disabled, missing credentials, timeout, provider error, empty result, and database fallback.
- [ ] Stored news remains the only AI-citable news evidence, and source-readiness/search links are not treated as citations.
- [ ] Social sentiment is separated from verified news or explicitly deferred.
- [ ] InStock integration is broken into independently verifiable modules with license attribution.
- [ ] Automatic trading is planned as a separate high-risk track with paper-trading-first safety controls before any live execution.
- [ ] Settings UI, if changed, remains localized, accessible, and consistent with existing Next.js Server Action patterns.

## Out Of Scope For The First Implementation Slice

- Live automatic trading, broker login, trade execution, or order routing in the first news/search provider slice.
- Cookie/proxy-based scraping workflows copied from InStock.
- Replacing this app's database, web UI, scheduler, or provider architecture with InStock's architecture.
- Implementing every InStock module in one commit.
- Storing licensed third-party full text without checking provider storage rights.
- Making paid provider calls in CI or deterministic tests.

## Recommended Task Split

1. First implementation slice: news/search provider registry and settings contract.
2. First implementation slice: news search adapter MVP with 1-2 providers plus fallback diagnostics.
3. Social sentiment adapter design and evidence boundary.
4. InStock analysis import slice: indicators or K-line pattern recognition.
5. InStock strategy/backtest slice after the analysis data contract is stable.
6. InStock automatic-trading safety foundation: paper-trading adapter, order-intent model, audit log, risk limits, kill switch, and broker-mocked tests. This is lower priority than non-trading InStock analysis features.

## Decisions

- First implementation slice: news/search provider registry, Anspire AI Search adapter, SerpAPI Baidu adapter, and degraded diagnostics.
- Automatic trading remains in overall scope but waits behind non-trading InStock analysis features and is out of scope for the first news/search provider slice.
- Non-trading InStock follow-ups should prioritize indicators, K-line pattern recognition, strategy screening, and backtest validation before automatic trading.
- Bocha and MiniMax remain registry-only until stable in-app API contracts are confirmed.

## Open Questions

No blocking open questions remain for the first implementation slice.
