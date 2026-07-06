# Professional Platform Comparison: Hard-to-find Source Notebook

## Purpose

This note reviews the implemented Source Notebook against the product direction:
a personal investment information aggregation cockpit focused on source
collection, macro/valuation indicators such as Buffett Indicator inputs, and
AI summaries/recommendations. It is explicitly not trying to become a
professional trading terminal.

## Sources Consulted

Official product/source references:

- Bloomberg Terminal: https://professional.bloomberg.com/products/bloomberg-terminal/
- Koyfin: https://www.koyfin.com/
- TradingView features: https://www.tradingview.com/features/
- AlphaSense platform: https://www.alpha-sense.com/platform/
- FRED API docs: https://fred.stlouisfed.org/docs/api/fred/
- SEC EDGAR APIs: https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- World Bank API docs: https://datahelpdesk.worldbank.org/knowledgebase/topics/125589-developer-information

Repo evidence inspected:

- `prd.md`, `design.md`, and `implement.md` for this task.
- `packages/services/research_source_notes.py`
- `apps/api/routers/research_source_notes.py`
- `apps/web/components/research-source-notebook.tsx`
- `apps/web/app/[locale]/evidence/page.tsx`
- `packages/services/market_dashboard.py`
- `packages/services/market_assistant.py`
- Source Notebook service/API/frontend tests.

## High-level Market Comparison

Professional finance platforms cluster around a few capabilities this product
should selectively learn from, not copy wholesale:

- Bloomberg Terminal prioritizes institutional market data, news, analytics,
  communications, and trading workflow integration. This is outside the
  personal cockpit scope except for the principle of strong provenance and
  fast cross-source navigation.
- TradingView emphasizes charting, alerts, screeners, community ideas, and
  brokerage-adjacent workflows. The current product should keep research-grade
  charting and signals, but avoid execution and low-latency terminal parity.
- Koyfin is closer to this product in dashboard spirit: market overview,
  watchlists, charts, macro/fundamental data, and custom views. The useful
  lesson is workflow organization: source notes, indicators, watchlists, and
  AI briefs should become one navigable research workspace.
- AlphaSense is the closest benchmark for hard-to-find research material:
  document search, transcripts, filings, broker research, and AI summarization.
  The current product should not mimic paid corpus entitlement, but should
  adopt the idea that every AI answer must point back to reviewed local
  evidence.
- FRED, SEC EDGAR, and World Bank are better treated as official source
  systems than competitor products. They should feed source-readiness,
  adapters, seed templates, and notebook review workflows only when licensing
  and evidence metadata are explicit.

## Does Source Notebook Satisfy the User Need?

Yes for an MVP.

The implemented Source Notebook directly addresses the user's direction:

- It gives the Evidence Center a persistent place for reviewed links, text
  excerpts, calculation notes, tags, symbols, and AI follow-up prompts.
- Browser file upload reads text into editable fields rather than creating a
  raw document corpus.
- Draft collection notes remain visible but non-citable.
- Only `reviewed` plus `AI-citable` entries produce stable
  `research_source_note:<id>` citations.
- Dashboard brief and market assistant citation flows consume only citable
  notebook entries.
- The implementation preserves the no-scraping, no-corpus, no-trading-advice
  boundaries.

This is the right product move because it fills the gap between "I found a
useful hard-to-find source" and "the AI can safely summarize it later with a
traceable citation." Professional platforms solve that with large proprietary
corpora; this product solves it with explicit personal review and local
evidence.

## Current Gaps

- Source notes are not yet strongly connected to source-readiness items,
  seed templates, or target macro indicator codes. A user can save a note, but
  the product does not yet clearly say which source gap or Buffett/FRED/PBOC
  input the note advances.
- Search/filter is useful but still basic. It is not yet a research retrieval
  surface comparable to professional document search.
- Review quality is binary. The product has `draft`, `reviewed`, and
  `is_citable`, but not a checklist-driven completeness score for source URL,
  source date, methodology, licensing note, calculation components, and
  whether the note is enough to support a macro observation.
- AI usage is citation-safe but not yet workflow-rich. The notebook stores
  `ai_follow_up`, but the UI does not yet turn notes into an explicit research
  question queue, brief input summary, or next-step plan.
- Document scope is intentionally narrow. That is correct, but future SEC
  filing/transcript workflows will need a separate rights, storage, and
  citation design before any full-text ingestion.

## Prioritized Improvement Plan

1. Link notebook entries to source-readiness and seed-template targets.
   Add structured optional fields or UI affordances for `source_id`,
   `target_indicator_codes`, and component role such as GDP, market cap,
   CPI source, M2 source, or filing note. This makes the notebook part of the
   macro/valuation evidence pipeline instead of a generic note list.

2. Add a review checklist and evidence completeness state.
   For citable rows, show whether the entry has source identity, URL or source
   document, as-of/published/retrieved date, excerpt, methodology/calculation,
   tags/symbols, and licensing/usage note. This borrows the diligence behavior
   of professional research systems without becoming a paid corpus platform.

3. Turn AI follow-up into a research queue.
   Surface saved `ai_follow_up` prompts as actionable questions from the
   Evidence Center and dashboard brief. The AI should answer only from allowed
   citations and should label gaps as "needs source" rather than inventing
   conclusions.

4. Improve notebook retrieval before adding more ingestion.
   Add stronger filters/saved views for source type, source name, symbols,
   tags, citable status, date range, and source-readiness category. This gives
   the user value closer to research platforms while staying personal and
   low-risk.

5. Add official-source-assisted collection only where contracts are clean.
   Next likely candidates are World Bank data for Buffett components and SEC
   metadata/search references. Keep them opt-in, metadata-first, and
   non-scraping. Do not ingest full documents or mark links as evidence until
   reviewed local excerpts and citation metadata exist.

6. Keep trading-terminal features low priority.
   Do not spend near-term product effort on execution, order routing,
   low-latency feeds, Level-2 parity, or terminal-style layouts. The durable
   advantage is source-transparent personal research synthesis: macro
   evidence, hard-to-find source collection, AI summaries, and review history.

## Product Verdict

The implemented Source Notebook is aligned with the product strategy and
meaningfully improves the personal research loop. It should be optimized next
around source-to-indicator linkage, review quality, retrieval, and AI follow-up
workflow. That path differentiates the app from professional trading terminals
while borrowing the right professional research discipline: every useful AI
summary should trace back to reviewed, local, auditable evidence.
