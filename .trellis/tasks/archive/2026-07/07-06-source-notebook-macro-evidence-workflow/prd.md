# Source Notebook Macro Evidence Workflow

## Goal

Turn the implemented Source Notebook from a generic personal source collection list into a macro/valuation evidence workflow.

The user need is a personal financial information aggregation and AI summary workspace, not a professional trading terminal. The workflow should help a user connect hard-to-find source notes to macro indicators and source-readiness gaps such as Buffett Indicator components, FRED/PBOC reviewed sources, seed templates, and AI-citable evidence boundaries.

The first MVP should make the path visible and usable:

`collect source -> review completeness -> link to macro/source target -> prepare seed evidence -> become AI-citable only when explicitly reviewed/citable`

## Background And Confirmed Facts

- The previous task `07-06-hard-to-find-source-notebook` implemented persistent `ResearchSourceNote` rows, browser text-file upload into editable excerpts, strict `reviewed + is_citable` citation boundaries, and dashboard/assistant citation integration.
- `ResearchSourceNote` already has `metadata_json`, which can store additive workflow metadata without a new migration for the MVP.
- `/evidence` already fetches source-readiness data through the market overview payload and renders source collection guidance and source-to-seed templates.
- `packages/services/information_sources.py` already exposes stable source IDs, categories, collection links, seed templates, and target indicator codes for FRED rates, inflation, liquidity, PBOC China M2, Buffett Indicator components, generated reports, news, future SEC/document sources, and user seed files.
- `packages/services/research_source_notes.py` already serializes `metadata`, validates citable status, and returns source-note citation payloads.
- The previous platform comparison recommends source-to-indicator linkage and review completeness before expanding ingestion or document search.

## Requirements

1. Source Notebook entries can be linked to an information-source readiness item such as `fred_us_rates`, `buffett_manual_valuation_components`, or `pboc_cn_m2_public_manual`.
2. Source Notebook entries can capture target macro/valuation indicator codes associated with the linked source, using source-readiness seed template targets where available.
3. Source Notebook entries can capture a component role such as market cap, GDP, CPI source, M2 source, rate source, yield-spread source, filing note, or general context.
4. The Evidence Center UI shows a review completeness checklist for source notes, including source identity, URL or source document, date/as-of metadata, excerpt, methodology/calculation note, tags/symbols or indicator targets, and license/usage note.
5. Completeness is advisory for this MVP: it helps the user review sources, but it does not automatically import macro observations or automatically make a note AI-citable.
6. AI citation boundaries remain strict:
   - draft notes remain collection records only;
   - linked source-readiness items and collection URLs are not citations;
   - only `reviewed + is_citable` Source Notebook rows enter dashboard/assistant allowed citations;
   - full filings/transcripts/raw documents remain out of scope.
7. Source note citations include source-linkage metadata when available, so AI summaries and diagnostics can show the note's source target, indicator targets, component role, and completeness state.
8. The Evidence Center shows which notebook entries advance a macro/source-readiness gap and which entries are ready for seed-preparation review.
9. Browser file upload remains a text-prefill convenience only; uploaded raw files are not stored as a managed corpus.
10. User-visible text is localized in English and Chinese.

## Acceptance Criteria

- [ ] The current Trellis task has `prd.md`, `design.md`, and `implement.md` before implementation starts.
- [ ] The Source Notebook form on `/evidence` can select a source-readiness target and component role, and can store target indicator codes in the saved note metadata.
- [ ] The Source Notebook form and saved-entry cards show a review completeness state/checklist derived from note fields plus workflow metadata.
- [ ] The Evidence Center can display source-linked notebook entries near the source-readiness workflow, so the user can see which notes advance FRED/PBOC/Buffett/user-seed gaps.
- [ ] Backend serialization and citation payloads preserve source linkage metadata without breaking existing Source Notebook API clients.
- [ ] Dashboard and assistant citations still include only reviewed/citable notes, and tests prove draft or non-citable linked notes are excluded.
- [ ] Source-readiness collection links and seed templates are still guidance only and do not become citations.
- [ ] Browser file upload behavior remains client-side text prefill only.
- [ ] English and Chinese message files contain all new user-facing labels.
- [ ] Focused backend and frontend tests cover metadata storage, completeness calculation/display, linkage display, localization, and citation-boundary behavior.

## Out Of Scope

- Automatic macro observation import from a note.
- Automatic scraping, crawling, OCR, PDF parsing, or raw binary file storage.
- Full document management or licensed research corpus ingestion.
- Trading advice, buy/sell/hold recommendations, target prices, position sizing, broker execution, or professional terminal parity.
- Account-level collaboration or multi-user permissions.
- AI follow-up queue execution. The note may still store `ai_follow_up`; turning it into a separate actionable research queue should be a follow-up task.

## Confirmed Scope Decision

The user confirmed the recommended MVP scope: implement source-to-indicator linkage plus review completeness only; leave AI follow-up queue execution for the next task.

Trade-off: including AI follow-up queue now would make the task larger and touch assistant UX more deeply. Keeping it out lets this task close the evidence workflow first.
