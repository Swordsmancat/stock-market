# Official disclosure metadata vertical slice

## Goal

Persist and expose official CNINFO A-share disclosure metadata as stable, auditable research evidence that can improve symbol-level AI analysis without claiming the document body has been ingested or reviewed.

## Confirmed Facts

- AkShare 1.18.64 exposes `stock_zh_a_disclosure_report_cninfo(symbol, market, keyword, category, start_date, end_date)` and returns code, company name, announcement title, publication time, and CNINFO detail URL.
- The platform already centralizes SQLAlchemy models in `packages/domain/models.py`, migrations in `alembic/versions/`, provider adapters in `packages/providers/`, business logic in `packages/services/`, and thin FastAPI routers in `apps/api/routers/`.
- Existing AI citation validation uses explicit prefix allowlists and accepts only locally persisted evidence.
- `ResearchSourceNote` is a manual-review notebook. It is not suitable as the canonical identity store for repeatable provider refreshes.

## Requirements

### R1. Official provider boundary

- Add a CNINFO disclosure metadata adapter behind an injectable provider boundary.
- Normalize symbols to six-digit A-share codes and validate `start_date <= end_date`.
- Accept only CNINFO detail URLs and extract a non-empty `announcementId` as the external document identity.
- Convert provider exceptions into sanitized diagnostics without leaking raw responses or request details.

### R2. Durable metadata identity

- Add a dedicated disclosure metadata table and Alembic migration.
- Persist source, source document ID, symbol, company name, title, category, published time, canonical URL, retrieval time, dedupe hash, and provider metadata.
- Enforce uniqueness for `(source, source_document_id)` and keep citation IDs stable across repeated refreshes.
- Refresh must upsert metadata and never delete existing records because a later provider response is empty or failed.

### R3. API and service behavior

- Provide a refresh endpoint for one symbol and bounded date range.
- Provide a list endpoint filtered by symbol with bounded pagination.
- Return counts for received, created, updated, unchanged, and rejected records plus sanitized diagnostics.
- A provider failure must return a controlled service/API error and leave stored records intact.

### R4. Metadata-only AI citations

- Provide citation IDs with prefix `official_disclosure:` only from persisted validated rows.
- Citation payloads must state `evidence_scope=metadata_only` and `content_ingested=false`.
- Integrate recent symbol-matching disclosure citations into the market assistant context and citation allowlist.
- The assistant may cite title, source, URL, category, and publication time, but must not claim facts from the undisclosed body.

### R5. Safety and compatibility

- No live network calls in automated tests; inject fake provider frames/adapters.
- Existing API consumers and citation types remain backward compatible.
- No document-body download, PDF parsing, embeddings, or vector search in this slice.
- No trading recommendations or execution behavior.

## Acceptance Criteria

- [x] A fake CNINFO response persists normalized metadata and returns stable `official_disclosure:` citation IDs.
- [x] Replaying the same response creates no duplicate row and reports unchanged/upsert counts accurately.
- [x] Changed title/category/URL metadata updates the existing external document identity without changing its citation ID.
- [x] Invalid symbols, inverted/unbounded dates, missing document IDs, non-CNINFO URLs, and invalid publication times are rejected deterministically.
- [x] Provider failure is sanitized, rolls back safely, and does not remove previously stored disclosures.
- [x] `GET /official-disclosures` returns newest-first symbol-filtered metadata with an explicit metadata-only boundary.
- [x] `POST /official-disclosures/refresh` delegates through the service/provider boundary and returns refresh diagnostics.
- [x] The market assistant includes recent persisted disclosure metadata for the requested symbol and accepts only known `official_disclosure:` IDs.
- [x] ORM/migration, service, API, provider, and assistant regression tests pass without external network access.
- [x] Documentation clearly states that disclosure bodies are not yet ingested or summarized.

## Out of Scope

- Full document/PDF content and section-level citations.
- Full-universe scheduled backfill and coverage thresholds.
- SSE/SZSE/BSE direct adapters beyond CNINFO's official disclosure channel.
- Evidence Center frontend browsing UI.
- Automatic interpretation of whether an announcement is positive or negative.
