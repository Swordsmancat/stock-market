# AI Research Brief and Follow-up Queue

## Goal

Turn the Evidence Center into a personal AI research action workspace by deriving a deterministic follow-up queue from already collected local evidence, Source Notebook notes, macro/source-readiness gaps, seed-template readiness, and existing dashboard brief context.

This product is a personal financial information aggregation and AI summary workspace. It should emphasize hard-to-find source collection, macro/valuation evidence preparation, and safe AI research prompts rather than competing with professional trading terminals.

## Scope Decision

The MVP will implement a deterministic, user-manageable follow-up queue only.

The queue may include AI-summary questions captured in Source Notebook `ai_follow_up`, but it will not execute those questions against an LLM and will not add a "generate AI brief from selected items" button in this slice. That AI brief execution workflow remains a follow-up task so this MVP can preserve citation boundaries and ship a useful research-action surface first.

## User Value

The user should be able to open the Evidence Center and quickly answer:

- What did the platform already collect and review?
- Which Source Notebook entries contain explicit AI follow-up prompts?
- Which macro/valuation sources are ready for seed preparation?
- Which source-readiness gaps still need manual research, adapters, or reviewed seed data?
- Which queue items can be supported by reviewed/citable local evidence, and which are only collection guidance?
- What should I investigate next without receiving trading advice?

## Confirmed Facts

- The task is in Trellis `planning`; implementation has not started.
- The archived `07-05-ai-research-retrieval-citations` task completed the single-instrument AI market assistant citation MVP. It supports daily bars, stored indicators, fundamentals, news, generated reports, reviewed Source Notebook citations, diagnostics, citation validation, deterministic fallback, and safety boundaries.
- The archived `07-06-source-notebook-macro-evidence-workflow` task completed Source Notebook source-readiness linkage, browser text-file prefill, target indicator metadata, component roles, and review completeness.
- `ResearchSourceNote` already stores `ai_follow_up`, `review_status`, `is_citable`, symbols, tags, dates, and workflow metadata.
- Source Notebook citations remain strictly gated by `review_status=reviewed` and `is_citable=true`.
- Source-readiness links, seed templates, draft notes, and non-citable notebook entries remain guidance or collection records, not AI citations.
- `/evidence` already receives market overview payloads with `information_sources`, macro/valuation indicators, dashboard brief narrative, and recent Source Notebook entries.
- `dashboard_brief.narrative` already provides a citation-aware overview of dashboard evidence, but it is not a user-manageable follow-up queue.
- Professional platforms are stronger at real-time market data, charting, screening, alerts, execution, and licensed content coverage. This project should instead optimize for personal source transparency, local evidence boundaries, and AI-summary readiness.

## Requirements

1. Evidence Center must expose a follow-up queue or equivalent research-action panel sourced from existing local payloads and services.
2. Queue derivation must use already available evidence:
   - Source Notebook `ai_follow_up`;
   - Source Notebook review completeness and source linkage metadata;
   - source-readiness statuses such as `needs_adapter`, `needs_manual_seed`, `no_data`, and `future`;
   - seed-template metadata for macro/valuation sources;
   - existing citable Source Notebook citation IDs when the note is reviewed and citable.
3. Queue items must be categorized so the user can distinguish at least:
   - source review follow-up;
   - macro/valuation seed-prep follow-up;
   - AI summary question;
   - source-readiness gap;
   - documentation, filing, news, or general research note when applicable.
4. Queue items must preserve citation/source boundaries:
   - reviewed/citable Source Notebook rows may expose their existing citation ID;
   - draft/non-citable notes may create collection tasks but must not expose a citation ID;
   - source-readiness links and seed templates may create next actions but must not become citations;
   - `ai_follow_up` text is a prompt/task, not evidence.
5. Queue items must display useful metadata when available: source target, target indicator codes, component role, completeness status, note title, source name/type, as-of/retrieved date, source-readiness status, and citation ID only when allowed.
6. Queue summary counts must make the research workload scannable, including total items and counts by item category or readiness state.
7. The UI must describe queue items as research prompts, source-review tasks, and evidence-preparation tasks. It must not present them as trading instructions.
8. English and Chinese user-facing strings must be updated together.
9. The implementation must reuse existing services and payloads where possible. No new persistent evidence store is required for the MVP.

## Acceptance Criteria

- [x] `prd.md`, `design.md`, and `implement.md` exist before implementation starts.
- [x] Evidence Center displays a follow-up queue or research-action panel near the Source Notebook and AI evidence summary.
- [x] Source Notebook entries with `ai_follow_up` appear as actionable AI-summary questions without becoming citations unless the note is reviewed and citable.
- [x] Draft/non-citable Source Notebook entries can generate collection or review tasks, but no queue item for them exposes a `research_source_note:<id>` citation ID.
- [x] Source-readiness gaps and seed-template readiness generate visible next actions without being represented as citations.
- [x] Follow-up items display useful metadata such as source target, target indicator codes, component role, completeness status, source-readiness status, and citation ID when applicable.
- [x] Queue summary counts make source-review, seed-prep, AI-summary, and source-gap workload visible.
- [x] Safety/copy makes clear that queue items are research prompts and evidence-preparation tasks, not trading advice or execution instructions.
- [x] English and Chinese localized strings are updated together.
- [x] Focused backend/frontend tests cover queue derivation, citation-boundary behavior, localized rendering, and no-trading-advice wording.

## Out Of Scope

- Automatic execution of AI follow-up questions against an LLM.
- A button to generate an AI brief from selected queue/evidence items.
- Multi-turn persistent assistant sessions.
- Watchlist-level monitoring or scheduled alerts.
- Automatic macro observation import from notebook entries.
- External scraping, crawling, OCR, PDF parsing, raw binary file storage, vector search, or licensed corpus ingestion.
- Production SEC filings, announcements, transcripts, or paid research providers.
- Trading advice, buy/sell/hold recommendations, target prices, position sizing, or execution workflows.

## Planning Status

Implementation is complete. Validation passed with focused backend/frontend checks, full `pytest`, full `npm run test:web`, ruff, TypeScript, and `git diff --check`.
