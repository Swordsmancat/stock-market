# AI Research Retrieval and Citation Enhancement

## Goal

Enhance the existing single-instrument AI market assistant with traceable research retrieval, a unified research evidence/citation layer, and stronger citation diagnostics. The task should use already available platform data sources first, while adding a compatible abstraction for future announcements, filings, transcripts, and research documents. The result should improve trust and professional usability without claiming Bloomberg, Koyfin, or AlphaSense parity.

## User Value

Users should be able to ask a stock-specific research question and see which platform sources supported the answer, when those sources were current, and which useful sources were missing or unavailable. The assistant must continue to avoid fabricated market data and direct trading instructions.

## Confirmed Facts

- The archived `07-04-ai-market-assistant` task delivered an MVP for `POST /assistant/market` with daily bars, indicators, fundamentals, news summaries, citations, diagnostics, safety metadata, deterministic fallback, and frontend rendering.
- The current assistant is a single-turn, single-instrument workflow. It is not a persistent research notebook, multi-turn chat session, or watchlist monitor.
- Existing response payload fields already include `answer_markdown`, `model`, `context`, `citations`, `diagnostics`, and `safety`.
- Existing citation objects have `id`, `label`, `source`, and optional `url` fields.
- Existing diagnostics have `source`, `status`, and `message`, but do not yet expose severity, machine-readable codes, freshness, or citation-validation details.
- Current assistant citations primarily cover daily bars. Indicators, fundamentals, news, and reports are not yet consistently represented as first-class citation items.
- Existing reusable data sources include:
  - market data bars and stored indicators,
  - fundamentals snapshots,
  - news articles and sentiment summaries,
  - generated reports with searchable content and stored citations.
- Formal announcements, filings, transcripts, document chunks, embeddings, and a unified research document index are not currently implemented as production data sources.

## Requirements

### R1. Preserve the Existing Assistant Contract

- Keep `POST /assistant/market` as the primary entry point.
- Preserve existing required request fields and existing top-level response fields.
- Add only backward-compatible optional citation and diagnostic fields.
- Keep current `ok`, `degraded`, `no_data`, and frontend error handling semantics compatible unless the design explicitly documents a narrower internal rule.

### R2. Add a Unified Research Evidence Layer over Existing Data Sources

- Retrieve and rank research evidence for the requested symbol and date range from available platform sources.
- MVP source priority should be:
  1. daily bars and derived price summary,
  2. stored technical indicators,
  3. fundamentals snapshot,
  4. news articles or news sentiment payload,
  5. generated reports when available.
- Add an internal research-evidence abstraction that can represent document-like sources such as announcements, filings, transcripts, and research notes when those production sources are added later.
- Do not add real external filing, transcript, paid research, or exchange-announcement providers in this task unless an existing implementation is discovered during execution.
- Missing optional sources must generate diagnostics instead of fabricated evidence.

### R2A. Prepare Future Document Retrieval without External Provider Scope Creep

- Define a stable internal shape for document-like evidence, including source type, title, excerpt/body summary, URL, as-of or published time, provider/source, and metadata.
- The implementation may add lightweight helper functions or service-layer dataclasses for research evidence, but should avoid introducing a vector database, embeddings pipeline, or broad public `/research/search` API unless the existing codebase already has a direct fit.
- If storage or API scaffolding is added, it must be minimal, testable, and clearly documented as a future integration point rather than a production filings/transcripts feed.

### R3. Strengthen Citation Coverage

- Generate stable citation items for each evidence source used in the assistant context.
- Citation IDs should remain deterministic and source-specific, for example `bars_1d:{symbol}:{as_of}`, `technical_indicators:{symbol}:{as_of}`, `fundamentals:{symbol}:{as_of}`, `news:{symbol}:{published_at_or_url_hash}`, and `generated_report:{report_id}`.
- Extend citations with optional metadata such as `source_type`, `as_of`, `provider`, `retrieved_at`, `excerpt`, or `metadata` where the backend can provide it safely.
- Include source URLs when available, especially for news articles.

### R4. Validate LLM Citation Use

- Prompt the LLM to use only citation IDs that exist in the response payload.
- Detect hallucinated or unknown citation IDs in generated answers when feasible.
- If validation fails, either degrade to the deterministic fallback or return a degraded answer with explicit diagnostics. The implementation must not silently present invalid citations as valid.
- Deterministic fallback output must remain traceable and include available citation context.

### R5. Improve Diagnostics

- Extend diagnostics with optional `severity`, `code`, `citation_id`, and `details` fields.
- Diagnostics should distinguish at least:
  - source has no data,
  - source unavailable due to service or session failure,
  - source omitted from retrieval,
  - stale or date-mismatched source when detectable,
  - citation validation failure,
  - deterministic fallback usage.
- Diagnostics must not leak secrets, API keys, hidden prompt content, or raw provider exception details beyond safe exception type/classification.

### R6. Frontend Citation and Diagnostic Display

- Keep the current assistant card UX and route proxy.
- Render citation URLs as safe links when present.
- Show added citation metadata in a compact form without overwhelming the existing card.
- Show diagnostic severity/code when present while preserving existing rendering for old payloads.

### R7. Safety Boundaries

- Preserve no-investment-advice, no direct buy/sell/hold instruction, no target price, no position sizing, no execution instruction, and no fabricated market data boundaries.
- Continue to avoid calling the LLM when core daily market data is unavailable.
- Continue to treat user questions as untrusted input.

## Acceptance Criteria

- [x] Existing assistant backend tests still pass after the response contract is extended.
- [x] Service tests prove citations are generated for available bars, indicators, fundamentals, news, and generated reports, using deterministic IDs.
- [x] Service tests prove missing optional sources produce diagnostics rather than fabricated citation items.
- [x] Service or AI tests prove hallucinated citation IDs from an LLM response are detected and handled as degraded or fallback.
- [x] API tests prove the response remains backward compatible and includes enriched citation/diagnostic fields when evidence is available.
- [x] Frontend tests prove citation links and diagnostic severity/code render correctly while existing no-data/degraded/error states remain functional.
- [x] Safety tests continue to prove direct trading instructions are refused or reframed.
- [x] Focused validation commands for backend and frontend pass.
- [x] Documentation or Trellis implementation notes record the remaining professional gaps, especially external filings/transcripts, persistent sessions, notebook workflows, and watchlist-level monitoring.

## Completion Status

The research-citation MVP is complete for the current platform scope. It uses existing platform sources first, adds backward-compatible citation metadata and diagnostic fields, validates LLM citation IDs, preserves safety boundaries, and renders enriched citation/diagnostic details in the assistant UI.

Professional research-terminal gaps remain out of scope for this slice: production filings/transcripts/announcements ingestion, vector search, multi-turn notebooks, persistent research sessions, paid research entitlement governance, and watchlist-level monitoring.

## Out of Scope

- New production ingestion for SEC filings, exchange announcements, transcripts, PDFs, or paid research feeds.
- Embedding/vector database infrastructure and semantic ranking.
- Multi-turn persistent assistant sessions.
- Watchlist-level narrative monitoring.
- Streaming assistant responses.
- Full markdown rendering overhaul, unless a small safe rendering change is required for citation links.
- Claims of parity with Bloomberg, Koyfin, TradingView, AlphaSense, or a professional terminal.

## Open Product Decision

- User decision on 2026-07-05: expand the task beyond the smallest existing-source MVP.
- Expansion boundary selected for implementation: use a medium-scope unified research evidence/citation layer. This task may add internal abstractions and testable service scaffolding for document-like evidence, but real external filings/transcripts/announcements providers, embeddings, and multi-turn notebooks remain follow-up work because the repository does not currently expose production sources for them.
