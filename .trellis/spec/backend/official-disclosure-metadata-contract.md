# Official Disclosure Metadata Contract

## Scenario: CNINFO A-share disclosure metadata

### 1. Scope / Trigger

- Trigger: a bounded symbol/date refresh persists CNINFO disclosure metadata and exposes it through API and symbol-level AI citations.
- Scope: `packages/providers/cninfo_disclosure_provider.py`, `packages/services/official_disclosures.py`, `packages/domain/models.py`, `alembic/versions/0017_official_disclosures.py`, `apps/api/routers/official_disclosures.py`, and `packages/services/market_assistant.py`.
- Non-goals: PDF/document-body download, parsing, summaries, embeddings, vector search, full-universe scheduling, or trading recommendations.

### 2. Signatures

- Provider:

```python
fetch_cninfo_disclosures(
    *,
    symbol: str,
    start_date: date,
    end_date: date,
    category: str | None = None,
    fetcher: Callable[..., Any] | None = None,
    retrieved_at: datetime | None = None,
) -> CninfoDisclosureFetchResult

_confirm_cninfo_empty_result(
    *,
    symbol: str,
    start_date: date,
    end_date: date,
    category: str | None,
    http_get: Callable[..., Any] | None = None,
    http_post: Callable[..., Any] | None = None,
) -> bool
```

- Service:

```python
refresh_official_disclosures(
    payload: OfficialDisclosureRefreshInput,
    *,
    session: Session,
    provider_fetcher=fetch_cninfo_disclosures,
) -> dict[str, object]

list_official_disclosures(*, session: Session, symbol: str, limit: int = 20)
list_citable_official_disclosure_citations(*, session: Session, symbols: list[str], limit: int = 3)
```

- API:
  - `GET /official-disclosures?symbol=<six-digit A-share code>&limit=1..200`
  - `POST /official-disclosures/refresh` with `symbol`, `start_date`, `end_date`, and optional `category`.
- Database identity: `official_disclosures` has unique `(source, source_document_id)`.
- Citation ID: `official_disclosure:<local UUID>`.

### 3. Contracts

- Symbols normalize from six digits or `.SH` / `.SZ` / `.BJ` suffixes to six digits.
- A refresh range is inclusive and may not exceed 366 days.
- The CNINFO adapter must lazily import AkShare and keep all dataframe column mapping inside the provider layer.
- AkShare raises `KeyError` after selecting columns from an empty DataFrame when the official response has zero announcements. Treat that exception as `no_data` only when a separate HTTPS CNINFO stock-list/query probe confirms the exact symbol/date range has `totalAnnouncement=0` and `announcements` is null/empty.
- The empty-result probe is fail-closed: category-filtered calls, nonzero official counts, missing symbols/org IDs, HTTP/JSON errors, or unexpected payloads do not suppress the original provider error.
- A valid row requires code, title, publication time, exact CNINFO detail path, and non-empty `announcementId` query value.
- `announcementId` is the external identity. A content hash detects metadata changes but never replaces external identity.
- Repeated refreshes upsert. Empty or failed refreshes never delete previously stored rows.
- Only persisted validated rows produce AI citations.
- Every citation must carry:

```json
{
  "evidence_scope": "metadata_only",
  "content_ingested": false,
  "allowed_claims": ["document_identity", "title", "publication_time", "category"]
}
```

- Metadata citations do not support claims about revenue, profit, risks, management statements, or any other document-body content.
- The market assistant accepts the `official_disclosure:` prefix only when the exact ID is present in its assembled local citation list.

### 4. Validation & Error Matrix

- Invalid/non-A-share symbol -> `ValueError`; API 422.
- `start_date > end_date` or range over 366 days -> `ValueError`; API 422.
- AkShare missing -> `CNINFO_PROVIDER_UNAVAILABLE`; API 502 with sanitized detail.
- Provider request failure -> `CNINFO_REQUEST_REJECTED` or `CNINFO_PROVIDER_ERROR`; API 502 without raw response data.
- AkShare `KeyError` + independently confirmed unfiltered official zero count -> empty fetch result; service `no_data`; no warning/backoff.
- AkShare `KeyError` + unconfirmed/nonzero/category-filtered probe -> `CNINFO_REQUEST_REJECTED`; scheduled monitoring preserves its cursor and enters retry backoff.
- Missing dataframe columns -> `CNINFO_SCHEMA_ERROR`; API 502.
- Invalid individual row (host/path/ID/time/length/symbol mismatch) -> reject that row, preserve valid rows, and return `CNINFO_ROW_REJECTED` diagnostic with row index only.
- SQLAlchemy write failure -> rollback batch and raise `OfficialDisclosurePersistenceError`; API 500 with a generic message.
- No valid rows -> `no_data`; no deletion and no fabricated citation.
- Non-A-share market-assistant symbol -> disclosure context is not applicable and does not create a warning diagnostic.

### 5. Good/Base/Bad Cases

- Good: CNINFO returns a valid `000001` annual-report title and detail URL; the service stores one row and the assistant may cite its title/publication time.
- Good: a repeated response reports `unchanged`; a corrected title for the same `announcementId` reports `updated` while preserving the local citation ID.
- Base: CNINFO returns no rows for the bounded range; the API returns `no_data` and existing metadata remains.
- Base: AkShare throws its empty-DataFrame `KeyError`, the official probe confirms zero rows, and the adapter returns `no_data` without erasing the last successful cursor.
- Bad: catch every AkShare `KeyError` as empty; this would hide a real dataframe/schema regression when CNINFO still reports announcements.
- Base: one row is invalid and one is valid; the valid row commits and the invalid row produces a sanitized rejection diagnostic.
- Bad: a search candidate or unpersisted provider row enters the assistant citation list.
- Bad: the assistant summarizes earnings, risks, or management commentary from a metadata-only title/link.
- Bad: an empty refresh is treated as authority to delete stored disclosures.

### 6. Tests Required

- Provider tests inject fake dataframes and assert argument mapping, timezone normalization, host/path/ID validation, schema errors, bounded ranges, row rejection, sanitized provider failures, independently confirmed zero-result recovery, and fail-closed nonzero/category probe behavior.
- Service tests use in-memory SQLite and assert create/update/unchanged counts, stable citation IDs, metadata-only flags, newest-first listing, and preservation after rejection/provider failure.
- API tests override the database session and monkeypatch refresh behavior; assert success delegation, 422 validation, and sanitized 502 mapping.
- Domain/migration tests assert the table, symbol index, and unique external-identity constraint.
- Assistant tests assert `official_disclosure` context/citation inclusion, metadata-only wording, and citation allowlist behavior.
- CI tests must never call live CNINFO/AkShare network paths.

### 7. Wrong vs Correct

#### Wrong

```python
citations.append({
    "id": f"official_disclosure:{candidate.source_document_id}",
    "excerpt": "The company reported strong earnings.",
})
```

This cites an unpersisted candidate and invents document-body meaning from metadata.

#### Correct

```python
refresh_official_disclosures(payload, session=session, provider_fetcher=fake_provider)
citation = list_citable_official_disclosure_citations(
    session=session,
    symbols=["000001"],
)[0]
assert citation["metadata"]["content_ingested"] is False
```

The local row owns the stable citation identity, and the citation explicitly limits claims to metadata.
