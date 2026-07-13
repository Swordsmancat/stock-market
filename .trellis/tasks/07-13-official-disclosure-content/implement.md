# Implementation plan

## Ordered Checklist

1. Add `pypdf>=6.14,<7`, the configurable document storage root, and Git ignore rule.
2. Add document-version/section ORM models and revision `0018` with SQLite/PostgreSQL-compatible types, foreign keys, indexes, and unique identities.
3. Add a CNINFO document provider for exact-ID attachment discovery and bounded allowlisted PDF download.
4. Add pure PDF extraction/chunking/heading/topic logic with generated-PDF unit tests.
5. Add service orchestration for disclosure lookup, versioned atomic storage, idempotent document/section persistence, listing, serialization, and section citation construction.
6. Add ingest/list FastAPI routes with explicit 404/422/502/500 mappings.
7. Add document-section context and `official_disclosure_section:` validation to the market assistant.
8. Add domain/migration/provider/extraction/service/API/assistant regressions and update README/user documentation.
9. Run focused Ruff/Mypy/pytest, full pytest, Alembic head/migration tests, and `git diff --check`.

## Validation Commands

```powershell
python -m pytest -q tests/providers/test_cninfo_document_provider.py tests/analytics/test_disclosure_documents.py tests/services/test_official_disclosure_documents.py tests/api/test_official_disclosures_api.py tests/ai/test_market_assistant.py tests/domain/test_models.py tests/domain/test_migrations.py
python -m ruff check packages/providers/cninfo_document_provider.py packages/analytics/disclosure_documents.py packages/services/official_disclosure_documents.py apps/api/routers/official_disclosures.py packages/domain/models.py tests/providers/test_cninfo_document_provider.py tests/analytics/test_disclosure_documents.py tests/services/test_official_disclosure_documents.py tests/api/test_official_disclosures_api.py
python -m mypy --follow-imports=skip --ignore-missing-imports packages/providers/cninfo_document_provider.py packages/analytics/disclosure_documents.py packages/services/official_disclosure_documents.py
python -m pytest -q
alembic heads
git diff --check
```

## Risk and Rollback Points

- CNINFO response fields are external schema: isolate parsing and fail closed on missing/changed attachment fields.
- PDF parsing is adversarial: enforce byte/page/text/section limits before persistence and never enable OCR implicitly.
- Filesystem/database dual writes are not one transaction: use content-addressed immutable files and idempotent retry.
- Long document text can expand prompts: assistant citations use bounded excerpts and a small limit.
- Do not run live CNINFO in tests; fake adapters and generated PDFs only.

## Review Gates

- Confirm every content citation points to a persisted section and exact document hash/page.
- Confirm metadata-only citations remain distinguishable from content citations.
- Confirm no absolute storage path or raw provider body appears in API responses/diagnostics.
- Confirm redirects, host/path changes, oversized files, malformed PDFs, and no-text PDFs fail closed.
- Confirm identical retries preserve IDs and changed files preserve prior versions.

## Validation Results

- Focused provider/extraction/service/API/assistant/domain suite: 61 passed.
- Full repository test suite: 625 passed.
- Changed-file Ruff: passed.
- Focused Mypy for provider, extraction, service, and router modules: passed.
- Alembic head: `0018_official_disclosure_documents`.
- `git diff --check`: passed (repository line-ending warnings only).
- Optional live CNINFO smoke for announcement `1225022887`: downloaded a 1,975,076-byte
  official PDF, verified SHA-256, and extracted 288 page-anchored sections from 288 pages
  without writing application database/storage state.
