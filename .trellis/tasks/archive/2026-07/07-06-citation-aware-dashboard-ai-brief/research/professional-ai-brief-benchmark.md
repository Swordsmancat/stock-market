# Research: Professional AI Brief Benchmark

- Query: how professional financial information products organize macro dashboards, AI summaries, citations/source coverage, and hard-to-find research inputs.
- Scope: planning support for citation-aware dashboard AI brief.
- Date: 2026-07-06.

## Findings

### Product Direction

The relevant professional benchmark is not execution or realtime terminal parity. It is evidence organization:

- Koyfin positions macro/market dashboards as customizable ways to view market context and macro themes.
- Bloomberg emphasizes AI over structured data, news, research, analytics, and large document collections.
- AlphaSense emphasizes generative AI summaries/search across trusted content such as filings, transcripts, news, and research documents.
- FRED provides official economic series and API observations that are useful source pipes for macro indicators.

The local product should borrow:

- cross-source synthesis.
- source/citation visibility.
- data-gap transparency.
- dashboard-level "what changed / why it matters / what next" workflow.

It should avoid:

- broker execution.
- low-latency feed parity.
- broad professional data entitlement management.
- unlicensed document scraping or transcript ingestion.

## Source Notes

- Koyfin official pages describe market/macro dashboards and customizable financial-data workflows: https://www.koyfin.com/ and https://www.koyfin.com/for-financial-advisors/financial-advisors/
- Bloomberg AI page describes ASKB and AI summaries across Bloomberg data, news, research, analytics, and documents: https://professional.bloomberg.com/products/bloomberg-terminal/ai/
- Bloomberg Terminal/research pages describe news analytics and professional research/data coverage: https://professional.bloomberg.com/products/bloomberg-terminal/ and https://professional.bloomberg.com/products/bloomberg-terminal/research/
- AlphaSense Smart Summaries and AI pages describe generative AI summaries/search across trusted content, filings, transcripts, news, and research: https://help.alpha-sense.com/hc/en-us/articles/41669307479443-Get-Instant-Insights-and-Save-Time-with-Smart-Summaries and https://www.alpha-sense.com/solutions/ai-in-financial-services/
- FRED API docs describe retrieving economic data series and observations through official web services: https://fred.stlouisfed.org/docs/api/fred/ and https://fred.stlouisfed.org/docs/api/fred/series_observations.html

## Repo Evidence

- `packages/services/market_dashboard.py` already builds deterministic dashboard sections, citations, diagnostics, and safety flags.
- `packages/services/information_sources.py` already maps official/missing/future source readiness.
- `packages/services/market_assistant.py` already implements LLM citation validation and deterministic fallback for instrument-level analysis.
- `.trellis/spec/backend/assistant-research-citation-contract.md` captures the reusable citation contract.

## Recommendation

Implement a dashboard narrative that uses the existing dashboard brief as evidence. The backend should:

- build a prompt from existing brief sections, citations, diagnostics, and information source readiness.
- call the configured LLM only when available.
- validate inline citation IDs against known dashboard citations.
- fall back to deterministic markdown when LLM is missing, fails, returns empty text, or cites unknown evidence.

This produces a visible AI feature without inventing new data, scraping documents, or competing with professional trading terminals.
