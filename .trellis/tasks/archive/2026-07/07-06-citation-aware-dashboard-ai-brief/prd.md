# Citation-aware Dashboard AI Brief

## Goal

Upgrade the personal dashboard brief toward citation-aware AI summaries that synthesize macro indicators, hard-to-find source readiness, reports, news, watchlist context, and data gaps without competing with trading terminals.

## Background

The product direction is a personal investment information aggregation and AI research cockpit. The highest-value dashboard capability is not low-latency trading data; it is a concise, source-aware summary of:

- macro/valuation observations such as Buffett Indicator, rates, CPI, M2, and related data gaps.
- watchlist freshness and followed-symbol context.
- generated reports and stored news that can be cited.
- information source readiness for official macro candidates, manual seeds, future filings/documents, and missing adapters.
- safe next research actions.

Current code already has the foundation:

- `packages/services/market_dashboard.py` builds `dashboard_brief` with deterministic sections, citations, diagnostics, and safety flags.
- `packages/services/information_sources.py` exposes source readiness and gaps.
- `packages/services/market_indicators.py` supports audited macro observations and offline seed imports.
- `packages/services/market_assistant.py` and `.trellis/spec/backend/assistant-research-citation-contract.md` already define the citation-aware assistant pattern: list known citation IDs, validate LLM inline citations, and fall back deterministically if citations are unknown or LLM is unavailable.

External benchmark check on 2026-07-06 supports this direction:

- Bloomberg and AlphaSense emphasize AI summaries/search over structured data, news, filings, transcripts, and research documents.
- Koyfin emphasizes customizable market/macro dashboards and broad research context.
- FRED is an official macro data source/API, not a trading terminal.

The MVP should borrow evidence density, source transparency, and AI synthesis from those products while avoiding execution, terminal parity, and unlicensed document scraping.

## Requirements

### R1. Citation-aware Dashboard Narrative

- Add an optional narrative layer to the existing dashboard brief.
- The narrative should summarize:
  - what changed.
  - why it matters.
  - what to watch next.
  - source/data gaps.
  - safety note.
- The narrative must use only citations already present in the dashboard payload.
- Unknown LLM citation IDs must be rejected and downgraded to deterministic fallback.

### R2. Deterministic Fallback

- If no LLM provider/API key is configured, return a deterministic fallback narrative.
- If LLM generation fails or returns empty content, return deterministic fallback with diagnostics.
- If LLM output cites unknown IDs, return deterministic fallback with a `CITATION_UNKNOWN_ID` diagnostic.
- Existing `sections`, `citations`, `diagnostics`, and `safety` fields must remain backward compatible.

### R3. Source Readiness Synthesis

- Include source readiness summary in the dashboard AI context.
- Treat `needs_adapter`, `needs_manual_seed`, `no_data`, and `future` as data gaps/next actions, not evidence citations.
- Do not imply FRED/PBOC/SEC/transcripts are configured unless local evidence exists.

### R4. Frontend Display

- Render the AI narrative near the existing dashboard brief.
- Show whether the narrative is LLM-generated or deterministic fallback.
- Keep citations and diagnostics visible.
- Keep the UI framed as personal research summary, not buy/sell recommendation.

### R5. Documentation

- Update README/manual to describe the citation-aware dashboard brief and fallback behavior.
- Explicitly keep "not investment advice", "no fabricated data", and "no trading terminal parity" boundaries.

## Acceptance Criteria

- [ ] Backend `dashboard_brief` includes an additive narrative/model payload while preserving existing fields.
- [ ] LLM generation uses only known dashboard citation IDs and validates inline citation IDs.
- [ ] Missing LLM config, LLM failure, empty response, and unknown citations fall back deterministically with diagnostics.
- [ ] Source readiness gaps are summarized as gaps/next actions, not citable evidence.
- [ ] Frontend renders the narrative, model/fallback state, citations, and diagnostics.
- [ ] Focused backend/frontend tests cover LLM success, fallback, unknown citation rejection, and visible UI rendering.
- [ ] README/manual document the current capability and boundaries.

## Out of Scope

- New official source adapters such as FRED/PBOC/SEC.
- Filings/transcripts/vector search/document ingestion.
- Persisted daily/weekly brief history.
- Trading advice, broker integration, realtime terminal workflows, or automatic execution.
