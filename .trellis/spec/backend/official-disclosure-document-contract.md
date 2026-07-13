# Official Disclosure Document Contract

## Scenario: CNINFO text-PDF ingestion and page-anchored citations

### 1. Scope / Trigger

- Trigger: a persisted `OfficialDisclosure` is explicitly ingested through its exact CNINFO announcement identity.
- Scope: `packages/providers/cninfo_document_provider.py`, `packages/analytics/disclosure_documents.py`, `packages/services/official_disclosure_documents.py`, `packages/domain/models.py`, migration `0018_official_disclosure_documents`, `apps/api/routers/official_disclosures.py`, and market-assistant citation assembly.
- Non-goals: OCR, whole-market/watchlist backfill, scheduling, vector search, LLM summaries, transcripts, paid research, or trading behavior.

### 2. Signatures

- Configuration: `DISCLOSURE_DOCUMENT_STORAGE_DIR`, default `data/official_disclosures`.
- Dependency: `pypdf>=6.14,<7`.
- Provider:

```python
discover_cninfo_attachment(
    *, symbol, org_id, announcement_id, published_at, post_json=None
) -> CninfoAttachment

download_cninfo_pdf(
    attachment_url, *, http_get=None, max_bytes=25 * 1024 * 1024, retrieved_at=None
) -> DownloadedPdf
```

- Extraction:

```python
extract_disclosure_pdf_sections(
    content,
    *,
    max_pages=500,
    max_total_chars=5_000_000,
    max_section_chars=4_000,
    max_sections=2_000,
) -> DisclosureExtractionResult
```

- Service:
  - `ingest_official_disclosure_document(disclosure_id, *, session, storage_root=None, ...)`
  - `list_official_disclosure_sections(disclosure_id, *, session, document_id=None, limit=100)`
  - `list_citable_official_disclosure_section_citations(*, session, symbols, limit=4)`
- API:
  - `POST /official-disclosures/{disclosure_id}/ingest-document`
  - `GET /official-disclosures/{disclosure_id}/sections?document_id=<optional>&limit=1..200`
- Database:
  - `official_disclosure_documents`, unique `(official_disclosure_id, sha256)`.
  - `official_disclosure_sections`, unique `(document_id, section_index)`.
- Citation prefix: `official_disclosure_section:`.

### 3. Contracts

- Attachment discovery posts to CNINFO's official announcement query and matches exact `announcementId` plus symbol. Title similarity is never identity.
- Only a relative `finalpage/.../<announcementId>.PDF` path may normalize to an HTTPS URL on `static.cninfo.com.cn` under `/finalpage/`.
- Download does not follow redirects and requires HTTP 200, allowed PDF content type, maximum 25 MiB, and `%PDF-` signature.
- CNINFO `adjunctSize` is provider metadata only; actual bytes and content length enforce the download boundary.
- Files are atomically stored as `<disclosure UUID>/<sha256>.pdf` below the configured root. API payloads do not expose absolute filesystem paths.
- Identical bytes reuse the document/section UUIDs. Changed bytes create a new immutable version and preserve prior evidence.
- Extraction keeps each section on exactly one one-based PDF page. Section text, topic, heading, and SHA-256 content hash are deterministic.
- Valid topics are `financials`, `operations`, `risks`, `major_events`, and `other`.
- Image-only, encrypted, malformed, page-limit, text-limit, and section-limit outcomes store no citable sections. OCR is never implicit.
- `official_disclosure:*` remains metadata-only. `official_disclosure_section:*` is content evidence and must include announcement ID, document SHA-256, page number, section index, heading, topic, content hash, official PDF URL, and bounded excerpt.
- Only the latest extracted document version per disclosure enters current market-assistant context. Older versions remain accessible through `document_id` for audit.

### 4. Validation & Error Matrix

- Invalid disclosure/document UUID -> `ValueError`; API 422.
- Missing disclosure or requested version -> `OfficialDisclosureDocumentNotFoundError`; API 404.
- Missing/invalid persisted CNINFO org ID -> validation error; API 422.
- Provider exception or invalid JSON/schema -> `CNINFO_DOCUMENT_PROVIDER_ERROR` / `CNINFO_DOCUMENT_SCHEMA_ERROR`; API 502 with sanitized detail.
- Exact announcement absent -> `CNINFO_DOCUMENT_NOT_FOUND`; API 502.
- Wrong symbol/type/path/filename/host/port/query/fragment -> identity/path/URL rejection; API 502.
- Redirect/non-200/wrong media type/oversize/bad signature -> deterministic download code; API 502.
- Unavailable storage root or atomic write failure -> `OfficialDisclosureDocumentStorageError`; API 500 with generic detail.
- SQLAlchemy write failure -> rollback and `OfficialDisclosureDocumentPersistenceError`; API 500.
- No text -> document `extraction_status=no_text`, HTTP 200, zero sections, `content_ingested=false`.
- Encrypted/malformed/limit failure -> document `failed` or `rejected`, HTTP 200, zero sections, non-citable diagnostics.
- Unknown `official_disclosure_section:*` in LLM output -> existing `CITATION_UNKNOWN_ID` fallback.

### 5. Good/Base/Bad Cases

- Good: exact CNINFO annual-report PDF downloads, hashes, stores, extracts page text, and creates stable section citations.
- Good: corrected PDF bytes create a second document version; current AI uses only the newest version while an operator can query the old version by UUID.
- Good: a deleted local file is restored on identical re-ingestion without changing document or citation IDs.
- Base: a valid image-only PDF is stored with `no_text`, explicit no-OCR diagnostic, and no citations.
- Base: malformed/encrypted/over-limit PDF is retained as non-citable document status with sanitized diagnostics.
- Bad: API accepts a caller-provided arbitrary download URL.
- Bad: `adjunctSize` is treated as bytes or trusted instead of measuring the response.
- Bad: metadata title is summarized as document body, or an older corrected version enters current AI context.
- Bad: file overwrite destroys the previous document hash/version.

### 6. Tests Required

- Provider tests inject CNINFO JSON and HTTP responses; assert exact-ID selection, pagination, URL/type/path/filename rules, redirects, status/media/signature/size boundaries, hashing, and secret-safe errors.
- Extraction tests generate PDFs in memory and assert page anchoring, topics, content hashes, no-text, encryption, malformed files, and every configured limit.
- Service tests use SQLite plus a temporary directory; assert atomic file creation, no absolute path exposure, idempotent IDs, changed-version retention, latest-only AI citations, old-version query, missing-file restoration, and non-citable no-text status.
- API tests monkeypatch services and assert success plus 404/422/502/500 mappings.
- Domain/migration tests assert both tables, foreign keys, indexes, and unique identities.
- Assistant tests assert known section citations appear and invented IDs are rejected.
- CI tests never call live CNINFO. Optional manual smoke may use an explicit known announcement ID and must not write production data.

### 7. Wrong vs Correct

#### Wrong

```python
pdf_url = request.json()["url"]
content = httpx.get(pdf_url, follow_redirects=True).content
citations.append({"id": f"official_disclosure_section:{announcement_id}"})
```

This permits SSRF/redirect substitution, skips byte/signature/hash provenance, and invents a citation before persistence.

#### Correct

```python
payload = ingest_official_disclosure_document(str(disclosure.id), session=session)
assert payload["document"]["sha256"]
assert all(
    citation["metadata"]["document_sha256"] == payload["document"]["sha256"]
    for citation in payload["citations"]
)
```

The service owns exact official identity discovery, allowlisted download, immutable storage,
persistence, and section citation construction as one idempotent operation.
