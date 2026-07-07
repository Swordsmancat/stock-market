# Source Ingestion Hub

## Goal

Build a focused source ingestion hub for a personal financial research workspace.

The hub should make it easier to collect hard-to-find online research inputs, local browser-uploaded text files, macro/valuation source notes, and AI follow-up prompts into the existing Evidence Center / Source Notebook flow. The product direction is information aggregation plus AI summary/recommendation support, not professional trading-terminal parity.

The first priority is to improve the Evidence Center / Source Notebook collection path itself: ingest reviewed material, use LLM-assisted extraction with deterministic fallback, extract a concise research summary, surface key indicator candidates, identify citation clues, and generate follow-up research questions. A later task can connect these prepared notes into a broader AI recommendation and summary panel.

## Background And Confirmed Facts

- `README.md` describes the app as a personal research platform for information aggregation, macro/valuation indicators, AI summaries, watchlist monitoring, and evidence-backed stock analysis.
- `/evidence` is already the Evidence Center for macro evidence, source readiness, source-to-seed templates, Source Notebook, and the deterministic research follow-up queue.
- The archived `07-06-hard-to-find-source-notebook` task implemented persistent `ResearchSourceNote` rows, manual source-note entry, client-side browser file reading for text-like files, reviewed/citable boundaries, and dashboard/assistant citation integration.
- The archived `07-06-source-notebook-macro-evidence-workflow` task linked Source Notebook entries to source-readiness targets such as Buffett Indicator components, FRED/PBOC macro sources, and user seed files.
- `apps/web/components/research-source-notebook.tsx` currently accepts `.txt`, `.md`, `.csv`, `.json`, and related MIME types, reads the selected file with `File.text()`, stores the filename in metadata, and places content into an editable excerpt field.
- `packages/services/research_source_notes.py` validates and serializes source notes; only `review_status=reviewed` and `is_citable=true` rows produce `research_source_note:<id>` citations.
- `packages/services/information_sources.py` already defines official/manual source readiness targets, collection links, seed templates, and target indicator codes for FRED rates, US CPI, US M2, PBOC China M2, Buffett Indicator components, generated reports, stored news, SEC/future documents, and user seed files.
- `packages/ai/provider.py`, `packages/ai/llm_factory.py`, and `packages/services/market_dashboard.py` already provide an OpenAI-compatible LLM path, platform settings lookup, deterministic fallback behavior, and citation validation patterns for dashboard narratives.
- `packages/services/research_follow_up_queue.py` already derives follow-up actions from Source Notebook fields and source-readiness gaps without executing LLM briefs.
- The current browser-file flow is useful but still embedded inside the notebook form. It does not provide a dedicated ingestion workflow, extraction preview, or AI-oriented summary/follow-up preview before save.

## Confirmed Product Decisions

- Route collected material into Source Notebook / Evidence Center first.
- Automatically extract summary, key indicators, citation clues, and follow-up research questions.
- Create a collection entry point for Buffett Indicator, macro indicators, and hard-to-find data sources.
- Use configured OpenAI-compatible LLM extraction when available, with deterministic/local fallback when the LLM is not configured, fails, returns invalid output, or returns empty content.
- Defer the full AI recommendation and summary panel to a later task.
- Keep this MVP limited to browser-readable text-like files (`.txt`, `.md`, `.csv`, `.json`) plus pasted text. PDF/OCR/raw binary document extraction is a follow-up scope.

## Requirements

1. Add an ingestion-focused workflow in the Evidence Center that helps the user collect online and local research material before it becomes a reviewed Source Notebook entry.
2. Preserve the existing citation boundary:
   - raw uploads, pasted text, URLs, and draft imports are collection material only;
   - nothing becomes AI-citable unless explicitly saved as a reviewed/citable Source Notebook row;
   - collection links and seed templates remain guidance, not citations.
3. Support browser-side file selection as a first-class ingestion path, reusing the existing client-side text-read pattern where appropriate.
4. Support the current text-like formats (`.txt`, `.md`, `.csv`, `.json`) and make accepted formats, extraction limitations, and failed-read states visible in the UI.
5. Stage extracted or pasted content into editable fields before saving so the user can clean excerpts, add source identity, link macro/source-readiness targets, add methodology/license notes, and write AI follow-up prompts.
6. Highlight macro and valuation workflows, especially Buffett Indicator component collection, PBOC/FRED/manual macro sources, and user seed files.
7. Add an AI-extraction step that can produce suggested source summary, key indicator candidates, citation clues, metadata fields, and follow-up research questions without building the later full AI recommendation/summary panel.
8. LLM extraction must be safe and bounded:
   - call the configured OpenAI-compatible provider only when available;
   - fall back deterministically when unavailable or invalid;
   - do not invent unsupported facts, data values, source URLs, dates, or citations;
   - expose extraction diagnostics/status to the UI.
9. Extract or suggest the following fields from staged content where possible:
   - concise source summary;
   - key indicator candidates, especially macro/valuation terms and Buffett Indicator components;
   - citation clues such as source name, URL/document identity, dates/as-of hints, methodology/calculation hints, and excerpt-worthy lines;
   - follow-up research questions suitable for the existing research follow-up queue.
10. Make Buffett Indicator, macro indicators, and difficult-to-find data sources first-class targets in the ingestion entry point.
11. Keep implementation additive to the existing Source Notebook, source readiness, and research follow-up queue contracts.
12. Localize all new visible UI text in English and Chinese.

## Acceptance Criteria

- [ ] The current Trellis task has `prd.md`, `design.md`, and `implement.md` before implementation starts.
- [ ] The Evidence Center exposes a clear Source Ingestion Hub entry point or panel distinct from the saved Source Notebook list.
- [ ] The hub accepts browser-selected text-like files and pasted content, previews extracted text, filename/source metadata, accepted-format guidance, and read errors before save.
- [ ] The hub can request LLM-assisted extraction from staged content and source-target context.
- [ ] The extraction response includes source summary, key indicator candidates, citation clues, metadata suggestions, follow-up research questions, extraction status, model/fallback metadata, and diagnostics.
- [ ] LLM extraction falls back deterministically when the provider is not configured, fails, returns empty text, or returns invalid JSON/unsupported fields.
- [ ] Extracted suggestions can be reviewed and edited before saving to Source Notebook fields such as excerpt, note, tags, target indicator codes, methodology/license notes, and `ai_follow_up`.
- [ ] The hub can stage content into a Source Notebook draft while preserving source-readiness target, target indicator codes, component role, methodology note, license note, tags/symbols, browser filename, extraction summary, extraction diagnostics, and AI follow-up prompt fields.
- [ ] The UI makes the reviewed/citable boundary visible: staged and draft items are not citations, and only reviewed/citable notes expose `research_source_note:<id>`.
- [ ] Macro/valuation source targets such as Buffett Indicator components are easy to select from the ingestion flow.
- [ ] Existing Source Notebook create/list behavior and citation payload contracts remain backward compatible.
- [ ] Focused backend/frontend tests cover extraction fallback behavior, LLM invalid-output fallback, file ingestion preview, staging-to-note payloads, citation-boundary behavior, localization, and macro/source-target defaults.

## Out Of Scope

- Automated web scraping, scheduled crawling, or bypassing website access restrictions.
- Trading advice, buy/sell/hold recommendations, target prices, position sizing, broker/execution features, or professional terminal parity.
- Automatically importing macro observations from a source note without a reviewed seed/import step.
- Automatically making uploaded files, extracted suggestions, or draft notes AI-citable.
- Persistent raw binary document storage.
- PDF parsing, OCR, full document management, full vector search, or long-term document corpus management in this slice.
- A full AI recommendation and summary panel; this follows after ingestion and extracted research notes are reliable.

## Planning Status

- This task is complex because it touches Evidence Center UX, Source Notebook payloads, source-readiness metadata, AI extraction, LLM fallback behavior, and tests. It needs `design.md` and `implement.md` before `task.py start`.
- No blocking open questions remain for the MVP scope.
