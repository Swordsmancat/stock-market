# Codebase Reuse Research

## Backend Findings

- `packages/domain/models.py` already defines `ResearchSourceNote` with `ai_follow_up`, `review_status`, `is_citable`, symbol/tag JSON, dates, and workflow metadata.
- `packages/services/research_source_notes.py` already normalizes Source Notebook fields, stores `ai_follow_up`, exposes serialized metadata, computes review checklist/completeness, and builds citable Source Notebook citations.
- `list_citable_research_source_note_citations(...)` centralizes the `reviewed + is_citable` boundary and should remain the only path for exposing `research_source_note:<id>` citation IDs.
- `apps/api/routers/research_source_notes.py` already supports creating and listing notes with source linkage, target indicator codes, component role, methodology/license notes, and `ai_follow_up`.
- `packages/services/information_sources.py` already returns queue-ready source-readiness fields: status, authority, `next_action`, `collection_note`, `citation_policy`, coverage, collection links, and seed templates.
- `packages/services/market_dashboard.py` already builds market overview, source-readiness payloads, dashboard brief citations, and source-gap counts. It is the likely integration point for an additive `research_follow_up_queue` payload.
- `packages/services/market_assistant.py` has an internal deterministic evidence-ranking pattern that can inform queue priority and stable ordering, but this MVP should not call the assistant or execute LLM generation.

## Frontend Findings

- `apps/web/app/[locale]/evidence/page.tsx` already fetches market overview and recent Source Notebook notes.
- Current render order is header metrics, seed import, Source Notebook, AI evidence summary, macro/valuation table, source-readiness workflow, and citation boundary. The best queue insertion point is after Source Notebook and before AI evidence summary.
- `apps/web/components/research-source-notebook.tsx` already captures `ai_follow_up` in the form and save payload, but saved note cards do not separately highlight the saved follow-up prompt.
- Existing UI patterns use `Card`, `Badge`, bordered panels, compact metadata chips, completeness checklists, and status badges.
- English/Chinese strings live in `apps/web/messages/en.json` and `apps/web/messages/zh.json` under `EvidenceCenter`, `EvidenceSeedImport`, and `ResearchSourceNotebook`.
- Existing tests cover Evidence Center page rendering, Source Notebook saved notes, browser file text upload, source target selection, seed templates, and API proxies.

## Likely Implementation Touchpoints

- `packages/services/research_follow_up_queue.py` or an equivalent service helper.
- `packages/services/market_dashboard.py`.
- `tests/services/test_market_dashboard_service.py`.
- `tests/api/test_dashboard_api.py`.
- `apps/web/app/[locale]/evidence/page.tsx`.
- `apps/web/app/[locale]/evidence/page.test.tsx`.
- `apps/web/messages/en.json`.
- `apps/web/messages/zh.json`.

## Citation Risks

- `ai_follow_up` is a task prompt, not evidence.
- Draft and non-citable notes can create queue items but must not expose citation IDs.
- Source-readiness links and seed templates are guidance only.
- Existing dashboard API tests already assert readiness IDs/template IDs are not dashboard citations; preserve that behavior.
- Queue ordering should be deterministic, ideally by explicit priority, kind, title/source label, and item ID.
