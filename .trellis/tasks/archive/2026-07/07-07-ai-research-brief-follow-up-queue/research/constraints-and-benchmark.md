# Constraints and Professional Benchmark Research

## Project Constraints

- Backend/frontend specs apply because this task crosses FastAPI/service logic and Next.js Evidence Center UI.
- Assistant citations must remain deterministic, source-specific, and validated.
- Evidence may come only from existing platform sources: daily bars, stored indicators, fundamentals, news, generated reports, and reviewed/citable Source Notebook rows.
- Draft/non-citable Source Notebook rows remain collection records.
- Browser file upload remains client-side text extraction into editable fields; the backend receives JSON/text, not raw files.
- Source-readiness statuses such as `needs_adapter`, `needs_manual_seed`, `no_data`, and `future` are data gaps or next actions, not citations.
- Seed templates and collection links are operator guidance until validated local observations exist.
- No scraping, OCR/PDF parsing, vector search, raw document corpus, production filings/transcripts ingestion, trading advice, target prices, position sizing, or execution workflow belongs in this MVP.

## Professional Platform Benchmark

Checked against official product pages on 2026-07-07:

- [Bloomberg Terminal](https://professional.bloomberg.com/products/bloomberg-terminal/) emphasizes integrated data, news, research, analytics, collaboration, charting, alerts, and multi-asset execution.
- [Koyfin features](https://www.koyfin.com/features/) emphasize full market data, portfolios, graphing, financial analysis, dashboards, and a clean investor workflow.
- [TradingView features](https://www.tradingview.com/features/) emphasize charts, alerts, screeners, financial analysis, macro/economic calendars, news, Pine Script, and strategy testing.
- [AlphaSense Smart Summaries](https://www.alpha-sense.com/platform/smart-summaries/) emphasizes AI summaries over curated professional content with snippet-level citations and verification.

## Product Implications

This project should not try to match Bloomberg or TradingView on terminal depth, execution, real-time feeds, alerts, broker workflows, or technical charting.

The closer benchmark for this task is AlphaSense-style trust and workflow shape:

- summarize only from known sources;
- preserve exact source/citation boundaries;
- make follow-up research questions explicit;
- help the user decide what to collect or review next;
- keep evidence gaps visible instead of fabricating coverage.

For a personal site, the strongest differentiator is a transparent evidence pipeline:

`source gap -> reviewed source note -> seed/import preparation -> local citable evidence -> AI summary`

The follow-up queue should make that pipeline visible and actionable.
