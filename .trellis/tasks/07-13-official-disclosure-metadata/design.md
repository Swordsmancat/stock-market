# Design: official disclosure metadata vertical slice

## Architecture

Data flow:

```text
CNINFO via AkShare
  -> CNINFO provider adapter
  -> normalized disclosure candidates
  -> disclosure service validation/upsert
  -> official_disclosures table
  -> list/refresh API
  -> symbol-level market assistant citation context
```

The provider adapter owns external dataframe field mapping and provider failures. The service owns validation, deduplication, persistence, serialization, diagnostics, and citation construction. Routers remain thin. AI code consumes only service-built citations from persisted rows.

## Domain Contract

`OfficialDisclosure` stores:

- UUID primary key used in the stable local citation ID.
- `source` and `source_document_id` as the official external identity.
- `symbol`, `company_name`, `title`, `category`, and `published_at`.
- `source_url`, `retrieved_at`, `dedupe_hash`, and `metadata_json`.
- created/updated timestamps.

The unique constraint is `(source, source_document_id)`. `dedupe_hash` covers normalized evidence fields for unchanged/update reporting; it is not the primary identity.

## Provider Contract

The CNINFO adapter accepts symbol, inclusive start/end dates, optional category, and an injectable fetch function. It invokes AkShare lazily so installations without the `cn-market` extra fail with a sanitized provider-unavailable error instead of breaking application import.

Rows are normalized into an immutable candidate dataclass. The adapter parses `announcementId` from the CNINFO detail URL and rejects rows that cannot establish official identity.

## Persistence and Transaction Contract

The service validates all returned candidates before committing the batch. Valid candidates are upserted by official identity. Invalid rows are reported as rejected without blocking valid rows. Provider-wide exceptions occur before writes; database exceptions roll back the transaction.

An empty successful provider response is not a deletion signal. Existing records remain untouched.

## Citation Contract

Citation ID: `official_disclosure:<local UUID>`.

Each citation includes source, provider, canonical URL, publication time, title, symbol/category metadata, and:

```json
{
  "evidence_scope": "metadata_only",
  "content_ingested": false
}
```

The assistant context summarizes only that an official disclosure with the given title was published. It must not summarize or infer body content.

## API Contract

- `GET /official-disclosures?symbol=000001&limit=20`
- `POST /official-disclosures/refresh`

Refresh input contains `symbol`, `start_date`, `end_date`, and optional `category`. Validation errors map to 422; provider unavailability/failure maps to a sanitized 502; unexpected persistence errors map to 500 without raw provider payloads.

## Compatibility and Rollback

- All new API fields/routes are additive.
- Removing the feature means excluding the router and assistant context; existing citations remain inert data.
- The migration downgrade drops only the new table.
- Document-body ingestion will be a later table/relationship or additive fields after its storage and rights policy is designed; metadata rows remain the canonical document identity.
