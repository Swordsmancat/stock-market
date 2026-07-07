# AI Research Brief Inbox

## Goal

Add a persistent AI research brief inbox to the Evidence Center so this personal finance workspace can turn local macro/valuation evidence, reviewed Source Notebook entries, and research follow-up prompts into reusable saved summaries.

The feature should reinforce the product direction: information aggregation, hard-to-find source collection, macro indicator evidence, Buffett Indicator research support, and AI synthesis. It should not compete with a professional trading terminal.

## Confirmed Facts

- The existing Evidence Center already renders macro/valuation indicators, information source readiness, dashboard brief narrative, Source Notebook, source-ingestion extraction, and a deterministic research follow-up queue.
- Source Notebook entries become AI-citable only when saved as `reviewed` and `is_citable=true`; only then do they expose `research_source_note:<id>` citation IDs.
- Source ingestion suggestions are editable collection notes only. They do not auto-save and do not become citations.
- Dashboard brief narrative already supports an OpenAI-compatible LLM with deterministic fallback and validates that generated inline citation IDs exist in the allowed citation list.
- Existing reports persist in `generated_reports`, but they are symbol-oriented stock reports. This task needs a separate research-brief record for macro/source/evidence synthesis.
- The repository uses SQLAlchemy ORM models plus Alembic migrations, FastAPI routers, Next.js API route proxies, `next-intl` messages, and focused pytest/Vitest coverage.

## Requirements

1. Saved research brief generation
   - Provide a backend API that generates and stores a research brief from the current local Evidence Center context.
   - Inputs should include the current dashboard brief, citable Source Notebook citations, information source gaps, and research follow-up queue items.
   - Use the configured OpenAI-compatible LLM when available and deterministic fallback when the provider is missing, fails, returns empty output, returns invalid output, or cites unknown citation IDs.
   - The generated brief must be concise markdown with sections for summary, key evidence, source/data gaps, suggested next research questions, and safety note.

2. Persistent inbox and history
   - Store generated briefs in a dedicated durable model/table rather than overloading stock generated reports.
   - Support listing recent saved briefs with title, scope, created time, model metadata, citations, diagnostics, source summary, and markdown content.
   - Support opening enough detail in the Evidence Center to reuse a previous brief without regenerating it.

3. Citation and evidence boundaries
   - A research brief may cite only local allowed citation IDs already present in the assembled context.
   - Source-readiness links, seed templates, draft notes, browser-upload suggestions, and follow-up queue items without citable source IDs must remain data gaps or research prompts, not evidence citations.
   - The API must reject or fall back from hallucinated citation IDs.

4. Personal research positioning
   - UI copy and safety metadata must frame the feature as personal information aggregation and AI research synthesis.
   - The feature must not produce buy/sell/hold calls, target prices, position sizing, trade execution advice, or low-latency/professional-terminal claims.

5. Evidence Center integration
   - Add the brief inbox to `/evidence` near the existing AI evidence summary and research follow-up queue.
   - Provide a clear action to generate a new saved brief and show recent saved briefs.
   - Keep existing Source Notebook and source-ingestion workflows intact.

6. Documentation
   - Update the user manual and README to describe the saved research brief inbox, LLM+fallback behavior, and citation boundaries.

## Acceptance Criteria

- [ ] Backend service can generate and persist a research brief from current Evidence Center context.
- [ ] Backend list API returns recent saved research briefs with stable IDs and serialized metadata.
- [ ] LLM output is validated against known citation IDs; invalid/empty/provider-failed outputs use deterministic fallback.
- [ ] Deterministic fallback includes evidence summary, source gaps, follow-up questions, diagnostics, and safety metadata.
- [ ] API tests cover create/list behavior, fallback behavior, and unknown citation rejection/fallback.
- [ ] A database migration creates the research brief table, and migration tests cover the expected columns.
- [ ] `/evidence` renders a generate action and a recent research brief inbox without breaking existing Source Notebook, dashboard brief, or follow-up queue rendering.
- [ ] Web proxy tests cover list/create proxy behavior.
- [ ] Page/component tests cover visible inbox state and generated brief feedback.
- [ ] README and manual explain that saved briefs are personal research records, not trading recommendations.

## Out Of Scope

- Full-text document corpus storage, vector search, or licensed research library ingestion.
- Automated scraping or scheduled external collection.
- Trading execution workflows, target-price generation, position sizing, buy/sell/hold recommendations, or broker integration.
- Manual per-source selection UI beyond the current Evidence Center context.

## Open Questions

None blocking for the MVP. Default scope is to generate from the current Evidence Center context first; more granular note/queue selection can be a later task.
