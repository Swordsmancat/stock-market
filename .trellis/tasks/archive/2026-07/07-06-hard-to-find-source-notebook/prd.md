# Hard-to-find Source Notebook

## Goal

Build a personal source notebook inside the Evidence Center for hard-to-find financial research inputs: reviewed links, uploaded excerpts, calculation notes, source provenance, tags, and AI follow-up notes.

The feature supports the product direction confirmed by the user: this app is a personal information aggregation and AI summary/recommendation workspace, with emphasis on macro indicators, valuation context such as Buffett Indicator inputs, and sources that are not easy to collect from normal trading websites. It is not intended to compete with professional trading terminals.

## Background

- The app already has `/evidence` as the evidence and source-readiness hub.
- `MarketIndicatorObservation` stores reviewed macro observations and can support citable macro evidence.
- `NewsArticle` and `GeneratedReport` are already used by assistant/dashboard citation flows.
- `packages/services/information_sources.py` tracks source readiness and currently treats document/filing style sources as future until ingestion, licensing, and citation metadata exist.
- `apps/web/components/evidence-seed-import-review.tsx` already provides a browser file upload and paste-review pattern for macro seed import.
- There is no persistent user-curated source note/notebook model yet.

## Requirements

- Add persistent source notebook entries for user-reviewed source collection.
- Each entry must capture source identity and provenance: title, source URL, source name, source type/category, retrieved date, optional published/as-of date, tags, symbols, excerpt, user note, AI follow-up note, and review/citation status.
- Support manual entry from the browser with paste fields for excerpt and notes.
- Support browser file upload for text-like source material, using client-side file reading to populate editable note/excerpt fields before saving.
- Show the notebook in or near the Evidence Center so it is part of the information collection workflow.
- Allow listing and filtering/scanning recent entries by status, source type, tags, symbols, and source name where practical for the MVP.
- Keep citation boundaries strict:
  - raw links, uploaded text, and draft notes are collection notes only;
  - entries become AI-citable only when explicitly saved as reviewed/citable and contain enough source metadata plus excerpt content;
  - uploaded files are not treated as a licensed document corpus or automatic scraping pipeline.
- Expose reviewed/citable notebook entries to AI summary context only through explicit citation payloads with stable IDs.
- Do not add scraping, scheduled crawling, licensed corpus ingestion, trading advice, buy/sell/hold recommendations, target prices, or position sizing.

## Acceptance Criteria

- [ ] A source notebook table/model exists with migration coverage and stores reviewed source metadata, excerpts, notes, tags/symbols, citable status, and timestamps.
- [ ] Backend service and API routes can create and list source notebook entries, validating required fields and citable-status requirements.
- [ ] The Evidence Center UI lets the user paste source notes and upload a browser file to prefill editable source content before saving.
- [ ] The Evidence Center UI displays saved notebook entries with provenance, status, tags/symbols, and excerpt/note previews.
- [ ] Citable notebook entries use a stable citation prefix and are included in dashboard or assistant AI evidence only when explicitly marked citable.
- [ ] Non-citable entries remain visible as collection notes but are not supplied as AI citations.
- [ ] User-visible text is localized in both English and Chinese message files.
- [ ] Focused backend, service, API proxy, and frontend tests cover create/list, validation, upload-driven UI population, display, and citation boundary behavior.

## Out Of Scope

- Automated web scraping or crawling.
- Full document management, binary file storage, OCR, PDF parsing, or licensed filing corpus ingestion.
- Multi-user sharing, permissions, or collaboration.
- Replacing macro seed import or existing market indicator observation storage.
- Professional trading-terminal functionality such as execution workflows, target prices, or position sizing.
