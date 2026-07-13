# Official disclosure document content and section citations

## Goal

Turn a persisted CNINFO disclosure metadata row into auditable local document evidence: discover the official PDF attachment, store a versioned file with a cryptographic hash, extract bounded page-anchored text sections, and expose only those stored sections as document-content AI citations.

## Background

- The metadata slice already persists stable CNINFO announcement identity and produces `official_disclosure:*` metadata-only citations.
- A live CNINFO response for announcement `1225022887` confirmed the official query payload includes `adjunctUrl`, `adjunctType`, and `adjunctSize`; the attachment is served from `static.cninfo.com.cn/finalpage/...PDF`.
- Metadata citations cannot support claims from the document body. AI needs locally stored text with page and content-hash provenance before it may cite document statements.
- The platform currently has no PDF dependency, raw-document storage policy, or document-section schema.

## Requirements

### R1. Official attachment discovery

- Discover the attachment by querying the official CNINFO announcement endpoint for one persisted disclosure.
- Match the exact CNINFO `announcementId`; never select a document by title similarity.
- Accept only `PDF` attachments from `static.cninfo.com.cn` under `/finalpage/`.
- Normalize the official relative attachment path to HTTPS and retain CNINFO-reported type/size as source metadata.
- Sanitize provider failures and never expose response bodies, headers, or request internals.

### R2. Bounded and safe document download

- Download one attachment at a time with explicit timeout and a 25 MiB maximum.
- Require HTTP 200, `application/pdf`-compatible content type, and `%PDF-` file signature.
- Revalidate the final URL against the allowlist; do not follow arbitrary redirects.
- Write atomically under a configurable local storage root ignored by Git.
- Name stored versions by disclosure UUID and SHA-256 so changed source files are preserved rather than overwritten.

### R3. Durable document and section identity

- Add document-version and extracted-section tables with Alembic migration.
- A document version is unique by `(official_disclosure_id, sha256)`.
- Each section is unique by `(document_id, section_index)` and stores page number, heading, topic, bounded text, and content hash.
- Re-ingesting identical bytes must reuse the existing version and stable section citation IDs.
- A changed file creates a new document version; old files and citations remain auditable.

### R4. Text extraction and classification

- Use `pypdf` for text PDFs; add an explicit project dependency.
- Extract page text deterministically, normalize whitespace, and split oversized pages into bounded chunks without mixing page numbers.
- Assign a deterministic topic from `financials`, `operations`, `risks`, `major_events`, or `other` using visible Chinese/English heading terms.
- Use a detected heading when available and fall back to `Page N`.
- Enforce maximum page count, total extracted characters, per-section characters, and section count.
- Encrypted, malformed, oversized, or image-only PDFs must produce explicit non-citable status/diagnostics; OCR is out of scope.

### R5. API and AI citation boundary

- Add `POST /official-disclosures/{disclosure_id}/ingest-document`.
- Add `GET /official-disclosures/{disclosure_id}/sections?limit=...`.
- Create `official_disclosure_section:<section UUID>` citations only from persisted extracted sections.
- Citations must include announcement ID, document SHA-256, page number, heading, topic, canonical attachment URL, and a bounded verbatim excerpt.
- Add recent symbol-matching section citations to the market assistant and its citation allowlist.
- Metadata citations remain distinct; the assistant must not imply that every disclosure has extracted content.

### R6. Safety and compatibility

- Automated tests use generated in-memory PDF bytes and fake CNINFO/HTTP adapters only; CI performs no live network calls.
- Existing metadata rows, APIs, and `official_disclosure:*` citations remain backward compatible.
- No OCR, vector search, whole-market backfill, scheduler, paid corpus, transcript ingestion, document summarization, or trading behavior.

## Acceptance Criteria

- [x] Exact-ID attachment discovery converts a valid CNINFO relative PDF path to an allowed HTTPS URL.
- [x] Wrong ID, wrong host/path/type, missing attachment, provider error, redirect, invalid PDF signature, and oversized content fail deterministically with sanitized diagnostics.
- [x] A valid generated text PDF is stored atomically with SHA-256 and produces page-anchored sections.
- [x] Re-ingesting identical bytes creates no duplicate document or section and preserves citation IDs.
- [x] Changed bytes create a new document version while the previous version remains queryable.
- [x] Image-only/no-text, encrypted, malformed, page-limit, character-limit, and section-limit cases never create citable sections.
- [x] Section citations contain exact document/page/hash/topic provenance and bounded extracted text.
- [x] List/ingest APIs map validation, not-found, provider, download, extraction, and persistence errors without leaking raw payloads.
- [x] The market assistant accepts known `official_disclosure_section:*` IDs and rejects invented IDs.
- [x] ORM, migration, provider, service, API, extraction, and assistant tests pass without external network access.
- [x] Documentation describes storage location, limits, metadata-vs-content citations, and the no-OCR/no-bulk boundary.

## Out of Scope

- Full-market or watchlist document backfill.
- OCR for scanned/image-only PDFs.
- Vector embeddings or semantic retrieval.
- LLM-generated document summaries.
- Direct SSE/SZSE/BSE document adapters beyond CNINFO.
- Automatic positive/negative event interpretation or trading decisions.
