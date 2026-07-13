# Design: official disclosure document content and section citations

## Architecture

```text
OfficialDisclosure row
  -> CNINFO attachment discovery (exact announcementId)
  -> allowlisted PDF downloader (bounded bytes)
  -> SHA-256 versioned atomic file storage
  -> pypdf page text extraction
  -> deterministic page chunks + topic classification
  -> OfficialDisclosureDocument + OfficialDisclosureSection rows
  -> list API + market-assistant section citations
```

Provider/network code owns CNINFO discovery and download validation. The service owns database lookup, storage paths, version identity, extraction orchestration, transaction behavior, serialization, and citations. Pure PDF text/chunk logic lives in analytics so it can be tested without database or network access.

## Data Model

### `OfficialDisclosureDocument`

- UUID primary key.
- Foreign key to `official_disclosures.id`.
- Official attachment URL, media type, CNINFO-reported size, actual byte size, SHA-256, storage-relative path, retrieved time, last-modified metadata, page count, extraction status/method, and metadata JSON.
- Unique `(official_disclosure_id, sha256)` preserves versions and makes identical ingestion idempotent.

### `OfficialDisclosureSection`

- UUID primary key.
- Foreign key to document version.
- Stable `section_index`, one-based `page_number`, heading, topic, content text, content hash, and created time.
- Unique `(document_id, section_index)`.
- Citation identity uses the local section UUID.

## Attachment Discovery Contract

`discover_cninfo_attachment(...)` receives symbol, org ID, announcement ID, and a narrow date range around the stored publication time. It posts to `https://www.cninfo.com.cn/new/hisAnnouncement/query`, follows bounded pagination, and returns only an exact-ID match.

The response `adjunctUrl` must be relative and normalize to:

```text
https://static.cninfo.com.cn/finalpage/<date>/<announcementId>.PDF
```

Unexpected absolute URLs, traversal segments, non-PDF type, or missing identity are rejected.

## Download and Storage Contract

- Default storage root: `data/official_disclosures`, configurable through `DISCLOSURE_DOCUMENT_STORAGE_DIR`.
- Maximum download: 25 MiB.
- No automatic redirects.
- Validate response status, content type, content length when present, final URL, and `%PDF-` signature.
- Stream/hash bytes, then atomically move a temporary file to `<disclosure UUID>/<sha256>.pdf`.
- Database paths are relative to the configured root; API payloads never expose an absolute server filesystem path.

## Extraction Contract

- `pypdf>=6.14,<7` is the pure-Python extraction dependency.
- Limits: 500 pages, 5,000,000 total extracted characters, 4,000 characters per section, and 2,000 sections.
- Text normalization preserves paragraph/newline boundaries needed for evidence while removing repeated whitespace.
- Each chunk belongs to exactly one PDF page.
- Heading detection prefers `第...节/章`, numbered headings, or short title-like first lines; otherwise use `Page N`.
- Topic classification is deterministic and keyword-based. It does not claim semantic completeness.
- No extracted text means `no_text`; no section rows and no content citations.

## Transaction and Failure Contract

Network/download/extraction happen before the database write batch. The raw versioned file may be present if a later database write fails; a retry with the same hash reuses it. Database exceptions roll back document/section rows. The service never deletes old versions as part of ingestion.

## Citation Contract

Citation ID: `official_disclosure_section:<section UUID>`.

Allowed claims are limited to the stored verbatim excerpt and its direct context. Citation metadata includes `announcement_id`, `document_sha256`, `page_number`, `heading`, `topic`, `content_hash`, `content_ingested=true`, and `evidence_scope=document_section`.

The market assistant loads a small recent set for the requested A-share symbol. Unknown section IDs trigger the existing citation-validation fallback.

## Compatibility and Rollback

- New tables/routes/prefix are additive.
- Existing metadata-only citations remain valid and distinct.
- Migration downgrade drops sections before document versions.
- Disabling document ingestion leaves metadata functionality intact.
- Removing stored files does not silently delete database evidence; missing-file diagnostics are handled on re-ingestion/maintenance paths.
