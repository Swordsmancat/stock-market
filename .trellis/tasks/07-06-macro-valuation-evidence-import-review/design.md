# Technical Design

## Architecture

Implement the import/review workflow as a thin UI and API layer over the existing market-indicator seed importer.

Recommended first slice:

- Backend service: extend `packages/services/market_indicators.py` with content-based preview/import helpers that reuse the existing row parser, audit metadata validation, known-code validation, and observation upsert path.
- Backend API: add a focused FastAPI router, preferably `apps/api/routers/market_indicators.py`, under `/market-indicators/seeds`.
- Frontend proxy: add Next.js route handlers under `apps/web/app/api/market-indicators/seeds/preview/route.ts` and `apps/web/app/api/market-indicators/seeds/import/route.ts` if the client component calls same-origin APIs.
- Frontend UI: add a client component embedded in `/evidence` or a child route such as `/evidence/import`.
- Documentation: update the user manual and developer maintenance runbook.

No new database table or Alembic migration is expected. Existing persistence remains `MarketIndicatorObservation`.

## Data Flow

```text
Browser paste/file picker
  -> client component reads text content
  -> POST /api/market-indicators/seeds/preview
  -> Next proxy forwards to FastAPI /market-indicators/seeds/preview
  -> service parses + validates + classifies rows without writes
  -> client renders row preview, errors, insert/update warnings

User confirms import
  -> POST /api/market-indicators/seeds/import
  -> FastAPI re-validates the same content
  -> service writes through existing upsert path in one transaction
  -> market-overview cache is cleared
  -> client shows success and links back to /evidence
```

Browser file upload is implemented as a file picker plus text read. The raw file is not persisted as a document or uploaded to storage.

## Backend Contracts

### Request Payload

Use a JSON request for both preview and import:

```json
{
  "content": "...raw JSON or CSV text...",
  "format": "json",
  "filename": "macro-seeds.json",
  "overwrite_acknowledged": false
}
```

Fields:

- `content`: required non-empty seed content.
- `format`: optional `json`, `csv`, or `auto`; default `auto`.
- `filename`: optional, used for format inference and display only.
- `overwrite_acknowledged`: import-only flag. Required when preview/import detects existing observations that will be updated.

Format inference order:

1. explicit `format` when it is `json` or `csv`;
2. `filename` extension `.json` / `.csv`;
3. first non-whitespace character `{` or `[` implies JSON;
4. otherwise treat as CSV.

### Preview Response

Preview should return HTTP 200 for both valid and invalid content because validation errors are expected user feedback:

```json
{
  "status": "valid",
  "can_import": true,
  "format": "json",
  "filename": "macro-seeds.json",
  "summary": {
    "rows": 2,
    "valid_rows": 2,
    "invalid_rows": 0,
    "inserts": 1,
    "updates": 1,
    "affected_codes": ["us_10y_yield"],
    "latest_as_of": "2026-07-03"
  },
  "rows": [
    {
      "row_label": "row 1",
      "status": "valid",
      "intent": "insert",
      "code": "us_10y_yield",
      "name": "US 10Y Treasury Yield",
      "category": "rates",
      "region": "US",
      "unit": "percent",
      "as_of": "2026-07-03",
      "value": "4.250000",
      "source": "Audited seed: FRED DGS10",
      "metadata": {
        "source_present": true,
        "method_present": true
      },
      "errors": []
    }
  ],
  "errors": []
}
```

Invalid preview should keep any safely parsed valid rows visible but set `status = "invalid"` and `can_import = false`.

### Import Response

Import should re-parse and re-validate the content. If content is invalid, return HTTP 422 with validation details and write nothing. If updates are detected and `overwrite_acknowledged` is false, return HTTP 409 with a preview-like response and write nothing.

Successful import:

```json
{
  "status": "imported",
  "observations": 2,
  "codes": ["us_10y_yield"],
  "latest_as_of": "2026-07-03",
  "summary": {
    "inserts": 1,
    "updates": 1
  },
  "cache": {
    "market_overview_cleared": 1
  }
}
```

## Service Design

Add dataclasses or typed dictionaries for preview rows and summary while keeping the existing CLI result backward compatible.

Suggested helpers:

- `parse_market_indicator_observation_seed_content(content, format_hint="auto", filename=None)`.
- `preview_market_indicator_observation_seed_content(content, session, format_hint="auto", filename=None)`.
- `import_market_indicator_observation_seed_content(content, session, format_hint="auto", filename=None, overwrite_acknowledged=False)`.

Implementation detail:

- Refactor existing private parser internals so file and content parsing share row parsing and audit validation.
- Preserve `import_market_indicator_observation_seed_file(...)` behavior for the CLI.
- Preserve all-or-nothing writes.
- Detect insert/update by querying `MarketIndicatorObservation` for each known `(indicator_id, as_of)` pair.
- Clear `dashboard:market-overview:*` cache after successful import. Cache clear failures must not fail the import.

## Frontend Design

Embed an import review client component near the top of `/evidence`, after the Evidence Center header/metrics or behind a clear import section. If the page becomes too dense, use `/evidence/import` and link from `/evidence`.

Expected controls:

- File picker accepting `.json,.csv,application/json,text/csv`.
- Text area for pasted seed content.
- Format selector: `Auto`, `JSON`, `CSV`.
- Preview button.
- Preview table with row status, code, name, as-of, value, source, metadata state, insert/update badge, and errors.
- Import button shown only after a valid preview.
- Overwrite acknowledgement checkbox when any update rows exist.
- Success panel linking back to `/evidence`.

Client behavior:

- Selecting a file reads the file text into the same text area.
- File name is sent as metadata for inference/display only.
- Preview and import use same-origin Next route proxies and no-store behavior.
- User-visible strings go in `apps/web/messages/en.json` and `apps/web/messages/zh.json`.

## Compatibility

- Existing `/dashboard/market-overview` payload remains backward compatible.
- Existing CLI import command remains available and keeps its current output contract.
- Existing seed templates remain collection guidance, not citations.
- Existing Evidence Center table should show newly imported observations after cache clear/refresh.

## Risks And Guardrails

- Risk: user accidentally overwrites a reviewed observation.
  - Guardrail: preview shows `update`, import requires overwrite acknowledgement when update rows are present.
- Risk: preview accepts a row that import rejects.
  - Guardrail: import reuses the same content parser and validation, then re-validates at confirm time.
- Risk: file upload turns into document storage.
  - Guardrail: browser reads text only; no raw seed files are stored.
- Risk: invalid rows partly import.
  - Guardrail: preserve all-or-nothing transaction behavior.
- Risk: Evidence Center shows stale macro evidence after import.
  - Guardrail: clear market-overview cache on successful import.

## Rollback

The first slice is additive. Rollback means removing the new API routes, route proxies, frontend import component/route, translations, and docs. Existing CLI import, market indicator tables, and Evidence Center display remain intact.
