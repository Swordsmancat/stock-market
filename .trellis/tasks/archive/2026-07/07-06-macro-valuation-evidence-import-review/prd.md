# Macro Valuation Evidence Import Review Workflow

## Goal

Build a personal Evidence Center workflow for importing reviewed macro and valuation seed observations from JSON/CSV content. The workflow should let the user preview validation results, understand which rows will become AI-citable local evidence, and explicitly confirm database writes.

This continues the product direction established by the Evidence Center: information aggregation, hard-to-find macro/valuation source collection, audited local observations, and AI summaries grounded in stored evidence. It is not a professional trading-terminal feature, live data feed, scraper, or trading recommendation tool.

## Background

Confirmed repository facts:

- `packages/services/market_indicators.py` already defines the supported macro/valuation codes: `buffett_indicator_cn`, `buffett_indicator_hk`, `buffett_indicator_us`, `us_10y_yield`, `us_2y_yield`, `us_10y_2y_spread`, `us_cpi_yoy`, `us_m2_yoy`, and `cn_m2_yoy`.
- `parse_market_indicator_observation_seed_file(...)` and `import_market_indicator_observation_seed_file(...)` already parse JSON/CSV files and enforce the audit contract.
- `scripts/import_market_indicator_seeds.py` already imports reviewed seed files through the service layer.
- The importer accepts JSON arrays or objects with an `observations` array. CSV input uses `code`, `as_of`, `value`, `source`, and `components_json`.
- Every row must include a known code, ISO `YYYY-MM-DD` date, decimal-compatible value, non-empty source, and audit components.
- Audit components must include at least one source metadata key: `source_url`, `source_series_id`, `source_document`, or `source_name`.
- Audit components must include at least one method/review key: `methodology`, `calculation`, `notes`, or `review_note`.
- Existing importer behavior is all-or-nothing. If any row fails validation, no observations are written.
- `MarketIndicatorObservation` has a unique constraint on `(indicator_id, as_of)`, and `upsert_market_indicator_observation(...)` updates an existing observation for the same indicator/date.
- `/evidence` already shows the Evidence Center: macro/valuation evidence table, source readiness, seed templates, AI summary, and citation boundaries.
- `GET /dashboard/market-overview` is the source for the Evidence Center payload and the AI dashboard brief.
- Source links and seed templates are collection guidance only; only validated local observations, generated reports, and stored news can become AI citations.

## Requirements

### 1. Import Review Surface

- Add a user-facing import/review workflow from the Evidence Center or a closely related route.
- The first screen should support both:
  - pasting reviewed JSON/CSV seed content;
  - selecting a local `.json` or `.csv` file through the browser file picker.
- Browser file upload is a convenience input path. The app should read the file content for preview/import, but must not store the original raw file as a document corpus.
- The workflow should be framed as personal evidence collection, not automatic ingestion or market-data scraping.
- The user should be able to return to the Evidence Center after import to see updated evidence and AI citation status.

### 2. Shared Backend Validation

- Add backend service support for previewing seed rows without writing database observations.
- Preview validation must reuse the same parser and audit rules as the existing importer.
- Preview must seed or read known indicator definitions before checking row codes, matching import behavior.
- Validation failures must include row labels and actionable messages.
- Preview must classify each valid row as `insert` or `update` based on whether an observation already exists for the same indicator/date.
- Preview must not write observations.

### 3. Explicit Confirmed Import

- Add a backend import endpoint or action that writes only after the user explicitly confirms.
- Confirmed import must reuse the existing all-or-nothing import/upsert behavior.
- If any row is invalid at confirm time, no observations are written.
- The response should report imported count, affected codes, latest as-of date, and whether rows were inserts or updates when practical.
- After import, dashboard/evidence caches must not leave the Evidence Center showing stale macro observations.

### 4. Frontend Review UX

- Show parsed rows before import, including code, name if known, category/region if available, value, unit, as-of, source, metadata presence, and insert/update state.
- Show invalid rows and global validation errors without pretending any valid rows were imported.
- Make no-data and rejected values visually distinct from `0`.
- Make the citation boundary explicit: rows become AI-citable only after a successful confirmed import.
- Show warnings for overwrites when a row would update an existing observation.
- Require an extra overwrite acknowledgement before importing when preview detects any `update` rows.
- Keep source links and templates as guidance, not citations.

### 5. Safety And Scope Boundaries

- Do not add scraping, scheduled macro jobs, background source crawling, broker execution, trading advice, buy/sell/hold recommendations, target prices, or position sizing.
- Do not store uploaded raw seed files as a licensed document corpus.
- Do not loosen the current audit metadata contract.
- Do not introduce a second parser or validation rule set that can diverge from the CLI importer.

### 6. Documentation

- Update the user manual with the import/review workflow and citation boundary.
- Update developer maintenance docs with focused validation commands.
- Mention that CLI import remains available for local/operator workflows.

## Acceptance Criteria

- [ ] A user can access a macro/valuation seed import review workflow from the Evidence Center.
- [ ] The workflow accepts reviewed JSON or CSV seed content by paste and by browser file picker.
- [ ] Preview validates seed content without writing database observations.
- [ ] Preview reports row-level success/failure, row labels, indicator code/name, as-of date, value, source, metadata state, and insert/update intent.
- [ ] Invalid preview results clearly state that no observations were imported.
- [ ] Confirmed import writes through the existing service-layer import/upsert path and remains all-or-nothing.
- [ ] A successful import response reports imported count, affected codes, latest as-of date, and clear next action to refresh/review the Evidence Center.
- [ ] Browser-selected seed files are read for preview/import but are not stored as raw source documents.
- [ ] If preview detects updates to existing observations, confirmed import requires an explicit overwrite acknowledgement.
- [ ] Existing Evidence Center AI citation boundaries remain true: only stored observations are citable, while links/templates are not.
- [ ] Existing CLI import behavior remains backward compatible.
- [ ] Tests cover service preview behavior, API preview/import behavior, all-or-nothing failures, update detection, frontend validation rendering, successful confirmed import, and route proxy/request forwarding if a Next.js proxy is added.
- [ ] Documentation describes the workflow, audit metadata requirements, overwrite/update semantics, and validation commands.

## Out Of Scope

- Automatic scheduled macro refresh jobs.
- New official adapters beyond existing FRED refresh paths.
- Scraping public websites or storing full source documents.
- Importing licensed research corpora, filings, transcripts, or large document sets.
- Professional trading-terminal workflows.
- Any investment advice, trading instruction, target price, position sizing, or execution language.

## Open Questions

No blocking product questions remain for MVP planning. The user chose to support both pasted JSON/CSV content and browser file upload.
