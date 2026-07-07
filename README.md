# Personal Investment Research Cockpit

Personal research platform for multi-market information aggregation, macro/valuation indicator tracking, AI summaries, watchlist monitoring, and evidence-backed stock analysis. The product direction is a source-transparent research cockpit, not a professional trading terminal.

## Quick start

1. Copy environment variables:

```bash
cp .env.example .env
```

2. Start infrastructure (PostgreSQL + Redis + optional API/workers):

```bash
docker compose up -d db redis
# full stack with API:
docker compose up -d db redis api worker beat
```

For A-share data providers:

```bash
pip install -e ".[cn-market]"
```

3. Install Python dependencies and run migrations:

```bash
pip install -e .
alembic upgrade head
```

4. Start backend API (separate terminal):

```bash
uvicorn apps.api.main:app --reload --port 8000
```

If port 8000 is occupied by an old process, use another port and set `API_BASE_URL` in `apps/web/.env.local`:

```bash
uvicorn apps.api.main:app --reload --port 8001
```

5. Start background workers (optional, for async tasks):

```bash
celery -A apps.worker.celery_app.celery_app worker --loglevel=info
celery -A apps.worker.celery_app.celery_app beat --loglevel=info
```

6. Start the web app:

```bash
npm install
npm run dev:web
```

If the frontend does not open, run the local health check before restarting services:

```bash
python scripts/dev_health_check.py
```

The check reports whether port 3000 is listening, whether `/zh` responds, and whether API/Redis/Celery dependencies are reachable.

Open [http://localhost:3000/en](http://localhost:3000/en).

## Documentation

| Document | Purpose |
|----------|---------|
| [docs/manual/user-guide.md](docs/manual/user-guide.md) | User-facing guide for personal research aggregation, macro/valuation indicators, AI summaries, and current capability status |
| [docs/runbooks/developer-maintenance.md](docs/runbooks/developer-maintenance.md) | Maintainer guide for endpoints, degraded-safe provider contracts, validation, and roadmap gaps |
| [docs/runbooks/local-development.md](docs/runbooks/local-development.md) | Full local setup, env vars, testing |
| [docs/runbooks/mvp-acceptance.md](docs/runbooks/mvp-acceptance.md) | Original MVP acceptance checklist |
| [CONTEXT.md](CONTEXT.md) | Domain terminology |
| [docs/superpowers/plans/2026-07-01-priority-5-6-7.md](docs/superpowers/plans/2026-07-01-priority-5-6-7.md) | Latest implementation plan |
| [docs/superpowers/plans/2026-07-01-implementation-gap-closure.md](docs/superpowers/plans/2026-07-01-implementation-gap-closure.md) | Current implementation status and gap-closure plan |

## Key features

- **Market data**: yfinance provider (US/HK/CN), provider-neutral `/ingestion/snapshot`, Celery scheduled ingestion
- **Information aggregation**: watchlists, market overview, generated reports, news/fundamentals context, provider diagnostics, and task-run status in one personal dashboard
- **Information source readiness**: explicit source registry for official macro candidates, valuation seed inputs, generated reports, stored news, future documents, and user-curated seed files, with official/legal collection links and citation boundaries
- **Macro and valuation indicators**: curated Buffett Indicator, rates, inflation, and liquidity definitions with explicit audited-source/no-data states
- **FRED macro adapter**: opt-in official FRED refresh path for US rates, yield spread, CPI YoY, and M2 YoY observations with source URL, series ID, retrieval time, and calculation metadata
- **Audited macro seed import**: JSON/CSV import path and dashboard seed templates for manually reviewed macro and valuation observations with required source and methodology metadata
- **Hard-to-find source notebook**: Evidence Center workflow for reviewed links, browser-uploaded text excerpts, calculation notes, tags/symbols, and AI follow-up notes, with explicit draft vs AI-citable boundaries
- **Source ingestion hub**: Evidence Center entry point that uses configured OpenAI-compatible extraction with deterministic fallback to turn pasted/browser-uploaded text into editable summaries, key indicator hints, citation clues, metadata suggestions, and follow-up research questions
- **Research follow-up queue**: deterministic Evidence Center queue that turns notebook AI follow-up prompts, source-review gaps, seed-prep actions, and source-readiness gaps into next research actions without executing LLM briefs
- **Saved research brief inbox**: Evidence Center generator that stores reusable AI research summaries from current local evidence, citable Source Notebook rows, source gaps, and follow-up prompts with LLM+fallback behavior and citation validation
- **AI summaries**: citation-aware dashboard narrative with deterministic fallback, generated reports, and citation-aware AI market assistant boundaries
- **Analysis pipeline**: technical indicators, fundamentals, news, AI daily reports, and research-safe recommendation signals
- **Watchlist alerts**: price/RSI rules with trigger history
- **Portfolios**: multi-portfolio CRUD with demo fallback
- **Task runs**: async ingestion/analysis with retry and report linking
- **Sector rotation**: provider-backed `/sectors/hot` contract with explicit data modes, fund-flow definitions, and degraded-safe fallback states
- **Dashboard UI polish**: compact market ticker, dense market-overview table, persisted China/international movement-color convention, durable screenshot evidence, and sampled light/dark WCAG contrast checks
- **Provider trust visibility**: shared frontend trust labels for provider/source/freshness/mock/degraded/no-data states across homepage ticker, market overview, recommendations, instrument detail, intraday chart, and reports

## Phase 2 / Phase 3 feature status

| Phase | Feature | Status | Notes |
|---|---|---:|---|
| P0 | Macro/valuation indicators + AI research brief | Implemented / citation-aware MVP | Dashboard overview now exposes a curated macro library covering Buffett Indicator, US yields/spread, CPI, US M2, and CN M2 definitions. Missing observations remain explicit `no_data`; the dashboard renders sections, citations, diagnostics, safety flags, and an additive citation-aware narrative. The narrative uses an OpenAI-compatible LLM only when configured and falls back deterministically if the model is unavailable, empty, failed, or cites an unknown ID. |
| P0 | FRED official macro adapter | Implemented / opt-in refresh MVP | `scripts/refresh_fred_macro_indicators.py` can refresh audited FRED observations for DGS10, DGS2, T10Y2Y, CPIAUCSL-derived YoY, and M2SL-derived YoY when `FRED_API_KEY` is configured. Tests use mocked HTTP responses; no automatic scheduling or dashboard citation occurs until observations are stored locally. |
| P1 | Information source readiness | Implemented / collection-guidance MVP | Dashboard overview now includes a source-readiness registry for FRED/PBOC-style macro candidates, Buffett manual seed inputs, generated reports, stored news, future filings/documents, and user seed files. It performs no live network fetches; it shows current local evidence, missing adapters/manual seeds, official/legal collection links, collection notes, citation boundaries, and next collection actions. |
| P1 | Audited macro seed import | Implemented / template-assisted manual import MVP | Reviewed JSON/CSV seed files can import macro and valuation observations into `MarketIndicatorObservation`. Each row requires source and audit/method metadata; imports validate all rows before writing and do not fetch live data. The source-readiness panel now shows seed templates, placeholder JSON/CSV rows, review checklists, and the import command for FRED/PBOC/Buffett-style inputs. |
| P1 | Hard-to-find source notebook | Implemented / reviewed-source MVP | `/evidence` now includes a persistent source notebook for user-reviewed links, excerpts, browser-uploaded text, calculation notes, tags/symbols, and AI follow-up notes. Draft notes remain collection records; only entries saved as `reviewed` and `AI-citable` produce `research_source_note:<id>` citations for the dashboard brief and market assistant. |
| P1 | Source ingestion hub | Implemented / LLM extraction MVP | `/evidence` now includes a source-ingestion panel inside the Source Notebook workflow. It accepts pasted text or browser-readable `.txt` / `.md` / `.csv` / `.json` files, calls the configured OpenAI-compatible LLM when available, and falls back deterministically to suggest summaries, key indicators, citation clues, editable metadata, and follow-up questions. Suggestions remain collection notes until the user explicitly saves a reviewed/citable Source Notebook row. |
| P1 | AI research follow-up queue | Implemented / deterministic queue MVP | `/evidence` now derives a research-action queue from Source Notebook `ai_follow_up`, review completeness, source-readiness gaps, and seed-template readiness. Queue items are prompts and evidence-preparation tasks; only reviewed/citable notebook rows expose `research_source_note:<id>` citation IDs, and this slice does not execute LLM briefs. |
| P1 | Saved research brief inbox | Implemented / LLM+fallback history MVP | `/evidence` can now generate and persist reusable research briefs from the current Evidence Center context. Briefs store markdown content, allowed local citations, source-gap/follow-up summaries, diagnostics, model metadata, and safety flags. OpenAI-compatible generation is used only when configured; provider failures, empty output, or unknown citation IDs fall back deterministically. |
| UI polish | Personal research dashboard surface | Implemented / evidence complete | Ticker, market overview table, settings-driven movement colors, durable screenshots, sampled WCAG contrast evidence, and major movement-color call sites are implemented and covered by web/browser evidence. The UI is optimized for personal scanning and research aggregation rather than terminal parity. |
| Phase 2 | K-line interaction enhancements | Complete | Interactive candlestick charts include range controls and MA / BOLL / volume / MACD / RSI / KDJ indicator controls. |
| Phase 2 | Smart recommendations | Complete | Breakout, oversold rebound, volume anomaly, and momentum-style research signals are available as research aids. |
| Phase 2 | Hot sector rotation | Partial / provider-backed MVP | `/sectors/hot` now returns a normalized provider contract with sector taxonomy, flow definitions, live/delayed/mock/unavailable data modes, top constituent metadata, breadth, contribution, provider capability, and explicit rotation-history availability. The default static fixture is explicitly `degraded + mock`; verified production fund-flow and persisted rotation history depend on provider availability such as AkShare/Tushare/Eastmoney-style integrations. |
| Phase 2 | Comparison analysis | Complete | Correlation-oriented comparison tooling is available. |
| Phase 3 | Intraday chart | Partial / provider-backed MVP | `GET /market-data/{symbol}/intraday` now supports verified yfinance `1m` minute bars when available, including previous-close references and `ok` / `no_data` / `degraded` payloads. Mock, AkShare, and Tushare remain degraded until explicit minute-bar providers are verified. |
| Phase 3 | Market depth | Partial / provider-boundary MVP | `GET /market-data/{symbol}/depth` now uses an explicit `fetch_market_depth` provider boundary, section-level `ok` / `degraded` semantics, verified order-book / recent-trade / fund-flow normalization, and large-order derivation only from verified trades. AkShare now has a fixture-tested order-book candidate path, but production-verified Level-2 status still requires opt-in live smoke checks, schema monitoring, and provider-permission validation. |
| Phase 3 | Technical indicator library | Complete | MACD, RSI, KDJ, MA, BOLL, and volume chart overlays are supported; backend MACD/KDJ persistence is covered. |
| Phase 3 | AI assistant | Partial / research-citation MVP | `POST /assistant/market` and the instrument-detail AI Market Assistant UI provide traceable, safety-bounded answers from verified daily bars, stored indicators, fundamentals, news, generated reports, and reviewed source notebook entries. Citations can include source metadata, excerpts, URLs, and diagnostic severity/code; production filings/transcripts, vector search, and broader watchlist monitoring remain follow-up work. |

See [docs/manual/user-guide.md](docs/manual/user-guide.md) for user-facing behavior and [docs/runbooks/developer-maintenance.md](docs/runbooks/developer-maintenance.md) for endpoint and provider-maintenance details.

## Audited macro seed import

Use reviewed local files to load hard-to-find macro and valuation observations:

```bash
python scripts/import_market_indicator_seeds.py path/to/macro-seeds.json
python scripts/import_market_indicator_seeds.py path/to/macro-seeds.csv
```

JSON accepts either a top-level array or an object with `observations`. CSV uses `code,as_of,value,source,components_json`. Each row must include a source reference such as `source_url` or `source_series_id`, plus a method/review field such as `methodology`, `calculation`, or `notes`.

This is an offline audited import path. It does not call FRED/PBOC/SEC, scrape websites, or turn seed values into investment advice.

## FRED macro refresh

Use the official FRED API only when a local API key is configured:

```bash
$env:FRED_API_KEY="..."
python scripts/refresh_fred_macro_indicators.py --series rates --latest-only --dry-run
python scripts/refresh_fred_macro_indicators.py --series all --start 2025-01-01 --end 2026-07-06
```

The refresh path writes through the same audited `MarketIndicatorObservation` evidence layer. It skips FRED missing values such as `"."`, derives CPI/M2 YoY only when prior-year source observations exist, and stores source series IDs, FRED URLs, retrieval timestamps, and methodology/calculation metadata. Missing API keys produce a `WARN`; provider or validation failures produce `FAIL`.

FRED source links and templates remain guidance only. AI summaries may cite FRED macro data only after this refresh stores validated local observations.

## Source collection guidance

The dashboard source-readiness panel now shows where to collect hard-to-find inputs before they can become AI evidence:

- FRED links for US rates, inflation, and liquidity candidates.
- PBOC public monetary-statistics guidance for China M2 manual review.
- World Bank links for Buffett Indicator market-cap/GDP and GDP components.
- SEC filing search links for future document workflows.
- Local report, news, and seed-file guidance for platform evidence.

These links are guidance only. They are not automatic ingestion, licensed document storage, web scraping, or dashboard-brief citations. AI summaries may cite a source only after reviewed data is stored locally with source, as-of, and methodology metadata.

For macro and valuation sources that can be imported manually, the same panel also shows source-to-seed templates: target indicator codes, required fields, placeholder JSON/CSV rows, a review checklist, and the import command. Template placeholders are not market data and are not import-ready until the user replaces them with reviewed values. Templates do not change source readiness status, do not write the database, and do not create AI-citable evidence until the audited import succeeds.

## Source notebook

The Evidence Center now includes a hard-to-find source notebook for personal research collection. Use it for reviewed links, local text/Markdown/CSV/JSON file excerpts read by the browser, valuation or macro calculation notes, tags, symbols, source-readiness targets, target indicator codes, component roles, methodology notes, license/usage notes, and AI follow-up prompts.

The Source Notebook also includes a Source Ingestion Hub. After pasting text or reading a browser file, use AI extraction to prepare an editable source summary, key indicator candidates, citation clues, metadata suggestions, and follow-up research questions. When an OpenAI-compatible LLM is configured, extraction uses it; otherwise provider failures, empty answers, or invalid JSON fall back to deterministic local extraction. Extraction suggestions are not citations and are not saved automatically.

Notebook entries are intentionally not a scraper or document corpus. The browser file picker reads text into editable fields; the backend stores the reviewed excerpt and notes, not raw binary files. Draft entries remain collection notes. A notebook entry becomes available to AI only when it is explicitly saved as `reviewed` and `AI-citable`; those rows produce stable `research_source_note:<id>` citation IDs that the dashboard brief and market assistant may use in their allowed-citation lists.

Source Notebook entries can now be linked to source-readiness targets such as FRED rates, PBOC China M2, or Buffett Indicator manual valuation components. Linked entries show target indicator badges and a review completeness checklist for source identity, URL/document, date metadata, excerpt, methodology, targets, and license/usage note. Completeness is review guidance only; it does not import observations or make a draft note AI-citable.

The Evidence Center also derives a research follow-up queue from the same local context. It surfaces notebook `ai_follow_up` prompts, source-review tasks, seed-prep actions, and source-readiness gaps as next research actions. Queue items are not LLM executions and not trading instructions; source links and seed templates stay guidance-only, while `research_source_note:<id>` appears only for reviewed/citable notebook rows.

The Evidence Center also includes a saved research brief inbox. Use it after reviewing sources and follow-up prompts to generate a durable research summary from the current local Evidence Center context. Saved briefs are stored separately from symbol-level generated reports and include markdown content, local allowed citations, source-gap counts, follow-up context, diagnostics, model metadata, and safety flags. The generator uses an OpenAI-compatible LLM only when configured and falls back deterministically when the provider is missing, fails, returns empty text, or cites an unknown ID.

Use this for information that normal trading sites do not organize well, such as Buffett Indicator source components, manual macro source checks, filing search notes, and one-off research excerpts. Keep full filings/transcripts, bulk scraping, licensed research corpora, and automated ingestion out of scope until source rights, storage policy, and citation metadata are designed.

## Tests

```bash
pytest
npm run test:web
```

## MVP 验收

```bash
python scripts/mvp_acceptance.py
```

需先启动 API（默认 `http://127.0.0.1:8000`，可通过 `API_BASE_URL` 覆盖）。

完整清单见 [docs/runbooks/mvp-acceptance.md](docs/runbooks/mvp-acceptance.md)。
