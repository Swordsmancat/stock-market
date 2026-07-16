# Market Indicator Seed Import Contract

## Scenario: Audited Macro And Valuation Seed Imports

### 1. Scope / Trigger

- Trigger: importing manually reviewed macro and valuation observations from local files.
- Applies to `packages/services/market_indicators.py` and `scripts/import_market_indicator_seeds.py`.
- The feature is for personal research evidence collection. It is not a live macro feed, scraper, or trading signal.

### 2. Signatures

- Service parse helper:
  - `parse_market_indicator_observation_seed_file(path: str | Path) -> list[MarketIndicatorObservationSeed]`
- Service import helper:
  - `import_market_indicator_observation_seed_file(path: str | Path, session: Session) -> MarketIndicatorSeedImportResult`
- CLI command:
  - `python scripts/import_market_indicator_seeds.py <seed_file>`
- Existing persistence path reused:
  - `upsert_market_indicator_observation(seed: MarketIndicatorObservationSeed, session: Session, commit: bool = True)`

### 3. Contracts

JSON input accepts either a top-level array or an object with an `observations` array. Each observation must include:

- `code`: known `MarketIndicator.code`.
- `as_of`: ISO date string in `YYYY-MM-DD`.
- `value`: decimal-compatible string or number.
- `source`: non-empty reviewed source note.
- `components`: JSON object with audit metadata.

CSV input must include:

- `code`
- `as_of`
- `value`
- `source`
- `components_json`: JSON object encoded as a CSV field.

`components` / `components_json` must contain at least one source reference key:

- `source_url`
- `source_series_id`
- `source_document`
- `source_name`

It must also contain at least one review or method key:

- `methodology`
- `calculation`
- `notes`
- `review_note`

### 4. Validation & Error Matrix

| Condition | Behavior |
|---|---|
| Unsupported extension | Raise `MarketIndicatorSeedImportError`; no writes. |
| Invalid JSON/CSV shape | Raise `MarketIndicatorSeedImportError`; no writes. |
| Missing `code`, `as_of`, `value`, `source`, or components | Raise `MarketIndicatorSeedImportError` with row label. |
| Bad `as_of` | Raise `MarketIndicatorSeedImportError`; date must be `YYYY-MM-DD`. |
| Bad `value` | Raise `MarketIndicatorSeedImportError`; value must parse as `Decimal`. |
| Components is not an object | Raise `MarketIndicatorSeedImportError`. |
| Missing source reference metadata | Raise `MarketIndicatorSeedImportError`. |
| Missing method/review metadata | Raise `MarketIndicatorSeedImportError`. |
| Unknown indicator code | Raise `MarketIndicatorSeedImportError`; no observations are upserted. |
| Any validation failure in a multi-row file | Validate-all-before-write; no partial observation imports. |

### 5. Good/Base/Bad Cases

- Good: `us_10y_yield` with `source_series_id="DGS10"` and `methodology`.
- Base: current curated definitions are seeded in the same transaction before validating codes.
- Bad: a row with only `value` and `source` but no `components` audit keys.
- Bad: a mixed file where row 1 is valid and row 2 has an unknown `code`; neither row writes an observation.

### 6. Tests Required

- Service tests must cover:
  - JSON object/array import.
  - CSV import with `components_json`.
  - missing source/method audit metadata.
  - unknown indicator code.
  - all-or-nothing behavior across multiple rows.
- Script tests must cover:
  - successful import with a test-local session factory.
  - validation failure without using the real configured database.

### 7. Wrong vs Correct

#### Wrong

```python
upsert_market_indicator_observation(
    MarketIndicatorObservationSeed(
        code="us_10y_yield",
        as_of=date(2026, 7, 3),
        value=Decimal("4.25"),
        source="FRED",
        components={},
    ),
    session=session,
)
```

This stores a value that the dashboard can cite, but it does not preserve the source series, URL, methodology, or review note that makes the value auditable.

#### Correct

```python
import_market_indicator_observation_seed_file(
    "macro-seeds.json",
    session=session,
)
```

The seed file must carry source and method metadata, the service validates every row first, and the existing observation upsert path remains the only persistence mechanism.

## Scenario: Seed Content Preview And Confirmed Browser Import

### 1. Scope / Trigger

- Trigger: previewing and importing manually reviewed macro and valuation seed observations from pasted JSON/CSV content or from a browser file picker that reads local `.json` / `.csv` text.
- Applies to `packages/services/market_indicators.py`, `apps/api/routers/market_indicators.py`, `apps/web/app/api/market-indicators/seeds/*/route.ts`, and `apps/web/components/evidence-seed-import-review.tsx`.
- The workflow is for personal evidence collection and AI-citable local observations. It is not a scraper, scheduled refresh job, trading recommendation, broker workflow, or document-corpus upload.

### 2. Signatures

- Service parse helper:
  - `parse_market_indicator_observation_seed_content(content: str, format_hint: str = "auto", filename: str | None = None) -> list[MarketIndicatorObservationSeed]`
- Service preview helper:
  - `preview_market_indicator_observation_seed_content(content: str, session: Session, format_hint: str = "auto", filename: str | None = None) -> MarketIndicatorSeedPreviewResult`
- Service import helper:
  - `import_market_indicator_observation_seed_content(content: str, session: Session, format_hint: str = "auto", filename: str | None = None, overwrite_acknowledged: bool = False) -> MarketIndicatorSeedImportResult`
- FastAPI endpoints:
  - `POST /market-indicators/seeds/preview`
  - `POST /market-indicators/seeds/import`
- Next.js same-origin proxies:
  - `POST /api/market-indicators/seeds/preview`
  - `POST /api/market-indicators/seeds/import`

### 3. Contracts

Request payload for preview:

```json
{
  "content": "{\"observations\": []}",
  "format": "auto",
  "filename": "macro-seeds.json"
}
```

Request payload for import:

```json
{
  "content": "code,as_of,value,source,components_json\n...",
  "format": "csv",
  "filename": "macro-seeds.csv",
  "overwrite_acknowledged": false
}
```

- `content` is required and must be non-empty seed text.
- `format` is optional and must be `auto`, `json`, or `csv`; default is `auto`.
- `filename` is optional and used only for format inference/display.
- `overwrite_acknowledged` is import-only and must be true when preview/import detects update rows.

Format inference order:

1. explicit `format=json` or `format=csv`;
2. `filename` extension `.json` or `.csv`;
3. first non-whitespace character `{` or `[` means JSON;
4. otherwise parse as CSV.

Preview response must include:

- top-level `status`, `can_import`, `format`, `filename`, `summary`, `rows`, and `errors`.
- per-row `row_label`, `status`, `intent`, `code`, `name`, `category`, `region`, `unit`, `as_of`, `value`, `source`, `metadata`, and `errors`.
- `intent` is `insert`, `update`, or `invalid`.
- `metadata.source_present` and `metadata.method_present` reflect the same audit metadata contract used by file imports.

Import success response must include imported observation count, affected codes, latest as-of date, insert/update summary, and cache-clear status when called through the API route.

### 4. Validation & Error Matrix

| Condition | Behavior |
|---|---|
| Empty `content` | Return preview/import validation error; no writes. |
| Unsupported `format` | Raise/return validation error; no writes. |
| Bad JSON/CSV shape | Preview returns `status=invalid`, `can_import=false`; confirmed import returns HTTP 422. |
| Any row violates the seed audit contract | Preview shows row-level errors and writes nothing; confirmed import returns HTTP 422 and writes nothing. |
| Unknown indicator code | Preview marks the row invalid; confirmed import writes nothing. |
| Existing `(indicator_id, as_of)` observation | Preview row intent is `update`. |
| Import has update rows and `overwrite_acknowledged=false` | API returns HTTP 409 with preview details; no writes. |
| Import succeeds through API | All rows are upserted through the service, then market-overview cache is cleared. |
| Cache clear fails after successful import | Import remains successful; cache failure must not roll back observations. |
| Browser file selected | Client reads `File.text()` into the same content flow; raw file is not stored as a document corpus. |

### 5. Good/Base/Bad Cases

- Good: user selects `macro-seeds.json` in `/evidence`, preview shows one `insert` row with source and methodology metadata, then confirmed import writes one local observation.
- Good: preview detects an existing `us_10y_yield` date as `update`; the import button stays disabled until the user acknowledges overwriting.
- Base: pasted CSV and browser-read CSV both use the same content parser and audit validation as the CLI file importer.
- Bad: preview writes definitions or observations as a side effect beyond reading/seeding known indicator definitions needed for validation.
- Bad: the browser upload path stores the raw file as a licensed document corpus.
- Bad: the UI treats source links, seed templates, or preview rows as AI citations before a confirmed import succeeds.

### 6. Tests Required

- Service tests must assert content JSON/CSV parsing, format inference, invalid row previews, no-write preview behavior, insert/update detection, all-or-nothing confirmed import, and overwrite acknowledgement enforcement.
- API tests must assert preview returns HTTP 200 for validation feedback, invalid confirmed import returns HTTP 422, missing overwrite acknowledgement returns HTTP 409, success returns import summary, and market-overview cache clear is attempted after success.
- Next.js proxy tests must assert upstream URL, method, status, content type, and payload forwarding for preview/import.
- Component tests must assert pasted preview, browser file text read, invalid/no-import messaging, update acknowledgement gating, successful import, and `router.refresh()` after success.
- Compatibility tests must keep `scripts/import_market_indicator_seeds.py` file import behavior unchanged.

### 7. Wrong vs Correct

#### Wrong

```typescript
await uploadRawFileToCorpus(file);
await fetch("/api/market-indicators/seeds/import", {
  method: "POST",
  body: JSON.stringify({ filename: file.name }),
});
```

This turns a convenience file picker into document storage and bypasses the reviewed content parser.

#### Correct

```typescript
const content = await file.text();
await fetch("/api/market-indicators/seeds/preview", {
  method: "POST",
  headers: { "content-type": "application/json" },
  body: JSON.stringify({ content, format: "auto", filename: file.name }),
});
```

The browser reads text into the same preview/import contract, keeps raw files out of storage, and only confirmed imports can create AI-citable observations.

## Scenario: Source-Readiness Seed Templates

### 1. Scope / Trigger

- Trigger: information-source readiness items expose optional seed-template guidance for audited local macro and valuation imports.
- Applies to `packages/services/information_sources.py`, `packages/services/market_indicators.py`, `scripts/import_market_indicator_seeds.py`, dashboard payload consumers, and focused tests.
- The templates are a preparation aid for personal research evidence collection. They are not provider APIs, live feeds, scrapers, automatic ingestion jobs, or trading recommendations.

### 2. Template Contract

Seed-template JSON and CSV examples must mirror the importer contract above:

- JSON examples use a top-level `observations` array.
- CSV examples use `code,as_of,value,source,components_json`.
- Each row includes the importer-required fields: `code`, `as_of`, `value`, `source`, and `components`.
- `components` / `components_json` must preserve source metadata such as `source_url`, `source_series_id`, `source_document`, or `source_name`.
- `components` / `components_json` must preserve method or review metadata such as `methodology`, `calculation`, `notes`, or `review_note`.

### 3. Boundaries

- Templates must use visibly non-real placeholders such as `YYYY-MM-DD`, `<reviewed decimal>`, and `<operator review note>`.
- Templates must not fetch FRED, PBOC, World Bank, SEC, exchange, or vendor URLs.
- Templates must not scrape pages, store documents, write database rows, or call `import_market_indicator_observation_seed_file(...)`.
- Template presence must not mark an information source as configured and must not change `status`, `evidence_count`, or `latest_as_of`.
- Template links and placeholder rows must not be added to `dashboard_brief.citations` or assistant `citations`.
- A macro or valuation value becomes citeable only after the user replaces placeholders with reviewed values and the audited seed import validates and stores a local `MarketIndicatorObservation`.

### 4. Good/Base/Bad Cases

- Good: FRED rates readiness shows placeholder rows for `us_10y_yield`, `us_2y_yield`, and `us_10y_2y_spread`, including series IDs and methodology placeholders, while remaining non-citeable until import.
- Good: Buffett Indicator readiness shows component-oriented placeholders for market cap, GDP, calculation notes, and reviewed source URLs.
- Base: a user seed-file template gives a generic import shape for any known macro indicator code without implying a source has been collected.
- Bad: a template includes realistic-looking sample yields, CPI values, or Buffett ratios that could be mistaken for market observations.
- Bad: `seed_template:fred_us_rates` or `fred_us_rates` appears in dashboard or assistant citation lists before a validated import creates local evidence.

## Scenario: China Macro Source Capability Matrix

### 1. Scope / Trigger

- Trigger: validating China macro source candidates before building any production NBS/PBOC/vendor/library adapter.
- Applies to `packages/services/source_capabilities.py`, `packages/services/information_sources.py`, `scripts/validate_china_macro_sources.py`, dashboard payload consumers, docs, and focused tests.
- The feature is a validation-only decision layer for personal macro information collection. It is not a data adapter, live feed, seed import, scraper, scheduled refresh job, or trading signal.

### 2. Signatures

- Service registry:
  - `CHINA_MACRO_SOURCE_CAPABILITIES: tuple[SourceCapability, ...]`
  - `get_china_macro_source_capability_payload() -> dict[str, object]`
  - `get_source_capability_by_id(source_id: str) -> SourceCapability | None`
- Additive source-readiness payload:
  - `get_information_source_readiness_payload(session)["source_capabilities"]`
- CLI command:
  - `python scripts/validate_china_macro_sources.py`
  - `python scripts/validate_china_macro_sources.py --source world_bank_china_macro --live-network`
  - `python scripts/validate_china_macro_sources.py --live-network --timeout 8`

### 3. Contracts

Capability items must serialize stable fields:

- `id`
- `label`
- `authority`
- `region`
- `indicator_families`
- `indicator_codes`
- `access_mode`: `official_api`, `public_page`, `manual_seed`, `vendor_api`, `library_wrapper`, or `unsupported`
- `adapter_status`: `implemented`, `adapter_ready`, `candidate`, `manual_only`, `blocked`, or `future`
- `credential_required`
- `license_note`
- `freshness_policy`
- `collection_links`
- `validation`: `{ status, checked_at, summary, diagnostics }`
- `citation_policy`
- `recommended_next_action`
- `probe_url`
- `is_ai_citable=false`

The matrix must include at least:

- NBS China macro candidate.
- PBOC China M2/manual source.
- World Bank China annual macro fallback.
- IMF or World Bank-style global fallback.
- Trading Economics or equivalent vendor API candidate.
- AkShare/Tushare-style library wrapper candidate.

`validate_china_macro_sources.py` defaults to no live network. Live probes run only with `--live-network`, perform shallow reachability/schema-marker checks, print `OK` / `WARN` / `FAIL`, and write no database rows.

### 4. Validation & Error Matrix

| Condition | Behavior |
|---|---|
| Default command without `--live-network` | Print `WARN` skipped probe rows and exit 0 unless source selection is invalid. |
| Unknown `--source` | Print `FAIL`, list supported source IDs, and exit nonzero. |
| Capability has no live probe URL | Print `WARN`; manual/license validation is required. |
| Live probe HTTP 2xx and expected markers present | Print `OK`; no observations are written. |
| Live probe HTTP 2xx but marker missing | Print `WARN`; schema must be inspected before adapter promotion. |
| Live probe HTTP 4xx/5xx | Print `FAIL`; keep source candidate/manual/blocked. |
| Live probe raises | Print sanitized exception class only; do not expose secrets, raw stack traces, or raw payload dumps. |
| Capability row appears in dashboard payload | It remains guidance only; it must not alter source readiness `configured`, `evidence_count`, or `latest_as_of`. |

### 5. Good/Base/Bad Cases

- Good: World Bank China annual macro is marked `adapter_ready` and documented as a low-frequency follow-up candidate without claiming monthly China macro coverage.
- Good: PBOC M2 remains `manual_only` until a stable machine-readable source is validated.
- Base: NBS live probe returns HTTP 403; source stays `candidate` and no adapter is built.
- Base: Trading Economics is listed as `vendor_api` with `credential_required=true`.
- Bad: `source_capability:nbs_cn_macro`, `nbs_cn_macro`, or a probe URL appears in `dashboard_brief.citations`, saved-brief citations, or assistant citations.
- Bad: a live probe `OK` row is treated as a stored China macro observation.
- Bad: an AkShare/Tushare wrapper is promoted to official evidence without recording upstream source, credential, license, and schema validation.

### 6. Tests Required

- Service tests assert required source families exist, payload fields serialize, summary/status counts are stable, and `is_ai_citable=false`.
- Script tests assert default no-network behavior, focused source selection, unknown source failure, fake live `OK`, fake schema-mismatch `WARN`, and sanitized live-probe failures.
- Information-source tests assert `source_capabilities` is additive and does not change existing source-readiness status/evidence semantics.
- Dashboard/API tests assert source gaps and citation lists do not include capability IDs or probe IDs.
- Type-check should cover the optional frontend `InformationSourcesPayload.source_capabilities` field.

### 7. Wrong vs Correct

#### Wrong

```python
citations.append({
    "id": "source_capability:nbs_cn_macro",
    "label": "NBS China macro statistics",
    "source": "source_capabilities",
})
```

This turns a source candidate and probe decision row into evidence before any audited local observation exists.

#### Correct

```python
payload["information_sources"]["source_capabilities"] = get_china_macro_source_capability_payload()
```

The matrix is additive decision metadata. It can guide the next adapter task, but AI may cite China macro values only after a follow-up adapter or audited seed import stores local `MarketIndicatorObservation` rows.

## Scenario: Official Macro Source Status Projection

### 1. Scope / Trigger

- Trigger: displaying official macro source configuration, browser-refresh readiness, local observation coverage, and homepage missing-favorite guidance.
- Applies to `packages/services/market_indicators.py`, `apps/api/routers/market_indicators.py`, and server-rendered frontend consumers of `/market-indicators/official-sources/status`.
- The projection is personal research workflow guidance. It is not refresh-run history, a scheduler, a trading signal, or a new AI citation source.

### 2. Signatures

- Service projection:
  - `get_official_macro_source_status_payload(session: Session) -> dict[str, object]`
- FastAPI endpoint:
  - `GET /market-indicators/official-sources/status`
- Relevant environment-backed settings:
  - `FRED_API_KEY`
  - `FRED_API_BASE_URL`
  - `WORLD_BANK_API_BASE_URL`

### 3. Contracts

The response must include:

- top-level `status`, `generated_at`, `providers`, and `citation_policy`.
- one provider row for `fred`.
- one provider row for `world_bank`.

Provider rows must serialize:

- `provider`
- `label`
- `status`: `ok`, `degraded`, `needs_configuration`, or a future additive status.
- `configured`
- `can_refresh_from_browser`
- `credential_required`
- `credential_configured`
- `credential_label`
- `base_url`
- `source_url`
- `source_frequency`
- `freshness_policy`
- `indicator_codes`
- `evidence_count`
- `latest_as_of`
- `missing_indicator_codes`
- `recommended_next_action`
- `citation_policy`
- `collection_links`

FRED covers:

- `us_10y_yield`
- `us_2y_yield`
- `us_10y_2y_spread`
- `us_cpi_yoy`
- `us_m2_yoy`

World Bank covers:

- `buffett_indicator_cn`
- `buffett_indicator_hk`
- `buffett_indicator_us`

FRED status must report whether `FRED_API_KEY` is configured without exposing the key. World Bank status must report `credential_required=false` and annual/lagged semantics.

### 4. Validation & Error Matrix

| Condition | Behavior |
|---|---|
| `FRED_API_KEY` missing or blank | FRED provider `status=needs_configuration`, `configured=false`, `can_refresh_from_browser=false`; no network call. |
| FRED key configured but some covered indicators lack local observations | FRED provider `status=degraded`; list missing indicator codes. |
| All FRED covered indicators have local observations and key is configured | FRED provider `status=ok`. |
| World Bank covered indicators missing local observations | World Bank provider `status=degraded`; list missing Buffett regions. |
| All World Bank covered indicators have local observations | World Bank provider `status=ok`. |
| Local observations exist but the official provider is not configured | Evidence count/latest date still reflect local observations, but browser refresh remains blocked. |
| Any secret value is present in settings | Response must include only configured booleans and labels, never the secret value. |

### 5. Good/Base/Bad Cases

- Good: FRED key is missing and one old `us_10y_yield` observation exists; status still blocks browser refresh while showing the local evidence count and latest date.
- Good: World Bank has no secret requirement and explains annual lag for Buffett Indicator context.
- Base: no observations exist; both providers return missing code lists and no fabricated values.
- Bad: status rows, collection links, base URLs, or dry-run diagnostics are added to dashboard or assistant citations.
- Bad: a missing FRED key hides already stored local observations.
- Bad: the status endpoint stores refresh attempts or mutates indicator observations.

### 6. Tests Required

- Service tests assert FRED configured/unconfigured states, World Bank no-secret state, evidence counts, latest as-of dates, missing code lists, and no secret leakage.
- API tests assert `GET /market-indicators/official-sources/status` returns the projection through the session dependency.
- Frontend tests assert Macro Research renders provider readiness beside refresh controls and homepage missing favorite cards show source-specific next actions.
- Dashboard/assistant tests must continue to assert source readiness/status rows are not AI citations.

### 7. Wrong vs Correct

#### Wrong

```python
return {
    "provider": "fred",
    "api_key": settings.fred_api_key,
    "last_refresh_status": "failed",
    "citation_id": "source_status:fred",
}
```

This leaks a secret, invents durable refresh history, and makes guidance look citeable.

#### Correct

```python
payload = get_official_macro_source_status_payload(session=session)
```

The projection is read-only, exposes safe configuration booleans, derives freshness from stored observations, and keeps status guidance outside AI citations.

## Scenario: Official FRED Macro Observation Refresh

### 1. Scope / Trigger

- Trigger: a maintainer explicitly runs `python scripts/refresh_fred_macro_indicators.py`.
- Applies to `packages/providers/fred_provider.py`, `packages/services/market_indicators.py`, and `scripts/refresh_fred_macro_indicators.py`.
- The feature is an opt-in official-source refresh path for personal research evidence. It is not an automatic live feed, scraper, trading signal, or background scheduler.

### 2. Contracts

- FRED configuration comes from environment-backed settings:
  - `FRED_API_KEY`
  - `FRED_API_BASE_URL`, defaulting to `https://api.stlouisfed.org/fred`.
- Missing API key produces a sanitized `WARN` and no network request.
- Provider errors must not expose API keys, full query URLs with secrets, raw stack traces, or raw provider payloads.
- Initial FRED mappings:
  - `DGS10` -> `us_10y_yield`
  - `DGS2` -> `us_2y_yield`
  - `T10Y2Y` -> `us_10y_2y_spread`
  - `CPIAUCSL` -> `us_cpi_yoy` through YoY calculation.
  - `M2SL` -> `us_m2_yoy` through YoY calculation.
- FRED missing values such as `"."` are skipped, never stored as zero.
- CPI/M2 YoY requires both current and prior-year source observations and skips derivation if either value is missing or the prior-year value is zero.
- Persistence must reuse `MarketIndicatorObservationSeed` and `upsert_market_indicator_observation(...)`.
- Each stored observation must satisfy the same audit metadata contract as manual seed imports.

### 3. Required Metadata

Stored FRED observations must include:

- `source_series_id`
- `source_url`
- `retrieved_at`
- `provider = "fred"`
- direct values: `methodology`
- derived values: `calculation`, `current_value`, `prior_year_value`, and `source_observation_dates`

### 4. Good/Base/Bad Cases

- Good: `DGS10` stores a direct percent observation with source series ID, FRED URL, retrieval timestamp, and methodology.
- Good: `CPIAUCSL` stores `us_cpi_yoy` only when current and prior-year CPI observations exist, with the YoY formula in components.
- Base: missing API key returns `WARN FRED refresh: FRED API key is not configured.` and writes nothing.
- Bad: FRED `"."` is stored as `0`.
- Bad: a FRED source-readiness link is cited before a local observation has been stored.
- Bad: an exception message includes the configured API key.

## Scenario: Official World Bank Buffett Indicator Refresh

### 1. Scope / Trigger

- Trigger: a maintainer explicitly runs `python scripts/refresh_world_bank_macro_indicators.py`.
- Applies to `packages/providers/world_bank_provider.py`, `packages/services/market_indicators.py`, `packages/services/information_sources.py`, and `scripts/refresh_world_bank_macro_indicators.py`.
- The feature is an opt-in official/public-source refresh path for personal research evidence. It is not an automatic live feed, scraper, trading signal, or background scheduler.

### 2. Signatures

- Provider:
  - `WorldBankProvider.fetch_country_indicator_observations(country_code, indicator_id, start_year=None, end_year=None, most_recent_values=None, per_page=100)`
- Service:
  - `refresh_world_bank_macro_indicators(session, target_group="all", start_year=None, end_year=None, latest_only=True, dry_run=False, provider=None, retrieved_at=None)`
- CLI:
  - `python scripts/refresh_world_bank_macro_indicators.py --target USA --dry-run`
  - `python scripts/refresh_world_bank_macro_indicators.py --target all`
  - `python scripts/refresh_world_bank_macro_indicators.py --target buffett_indicator_us --start-year 2020 --end-year 2024 --no-latest-only`
- Environment:
  - `WORLD_BANK_API_BASE_URL`, defaulting to `https://api.worldbank.org/v2`.

### 3. Contracts

- Initial World Bank mappings:
  - `USA` + `CM.MKT.LCAP.GD.ZS` -> `buffett_indicator_us`.
  - `CHN` + `CM.MKT.LCAP.GD.ZS` -> `buffett_indicator_cn`.
  - `HKG` + `CM.MKT.LCAP.GD.ZS` -> `buffett_indicator_hk`.
- Optional same-year GDP context:
  - `NY.GDP.MKTP.CD` is fetched for component metadata only; it is not a separate macro indicator in this slice.
- `most_recent_values` must be sent to World Bank as the documented `mrv`
  query parameter. With no explicit year range, both default and `latest_only`
  refreshes request the existing bounded five-value window; `latest_only`
  selects the maximum valid observation locally after null rows are skipped.
- World Bank also documents `MRNEV` for recent non-empty values, but this refresh
  deliberately avoids that path because live probes reproduced latency beyond
  45 seconds. Do not reduce the `mrv` window to one row, which can lose a lagged
  annual series when its newest row is null.
- The default World Bank request timeout is a bounded 30 seconds so normal
  official-API latency above ten seconds does not cause a premature failure.
- World Bank year strings are stored as annual observation dates on December 31 of that year.
- Missing/null/invalid World Bank values are skipped, never stored as zero.
- Persistence must reuse `MarketIndicatorObservationSeed` and `upsert_market_indicator_observation(...)`.
- Each stored observation must satisfy the same audit metadata contract as manual seed imports.
- Source readiness may expose a World Bank adapter-backed Buffett source, but readiness IDs, links, templates, and diagnostics are not citations.

### 4. Validation & Error Matrix

| Condition | Behavior |
|---|---|
| World Bank response is not the expected `[metadata, rows]` list | Raise `WorldBankProviderError`; no writes. |
| HTTP/network/provider exception | Raise sanitized `WorldBankProviderError` with the raw cause suppressed; neither the message nor formatted exception chain may expose raw tokens, full payload dumps, or stack traces. |
| World Bank exceeds the bounded 30-second request timeout | Raise sanitized `WorldBankProviderError`; do not retry implicitly or write partial/fabricated observations. |
| Row date is not a valid year | Skip row and count a diagnostic. |
| Row value is null, blank, non-decimal, or non-finite | Skip row and count a diagnostic. |
| No valid rows for a target | Return zero observations for that target with diagnostics; do not fabricate a value. |
| GDP component fetch fails | Preserve the ratio observation when valid and add a sanitized diagnostic for missing GDP context. |
| Unknown `target_group` | Raise `ValueError`; script prints `FAIL` and exits nonzero. |
| `dry_run=true` | Fetch and validate, then roll back; no `MarketIndicatorObservation` rows remain. |
| Validation fails after definitions are seeded | Roll back all observation writes. |

### 5. Good/Base/Bad Cases

- Good: `USA` stores a `buffett_indicator_us` observation from `CM.MKT.LCAP.GD.ZS`, with World Bank provider, country code, indicator ID, source URL, retrieved timestamp, methodology, and same-year GDP context.
- Good: source readiness shows a distinct World Bank Buffett adapter item while keeping the manual Buffett seed item as fallback.
- Base: GDP context is unavailable; the ratio observation can still be stored if it has valid source and methodology metadata.
- Base: annual data is lagged; missing current-year values are diagnostics/source gaps, not market signals.
- Bad: a World Bank collection link or source-readiness ID is copied into dashboard or assistant citations before a local observation exists.
- Bad: `None` or missing values are stored as `0`.
- Bad: World Bank annual data is described as real-time or low-latency market data.

### 6. Tests Required

- Provider tests assert successful parse, the `mrv` query key (and absence of
  `mrnev`), the bounded 30-second default timeout, missing/null skip behavior,
  pagination, unexpected shape failure, and sanitized provider errors whose
  formatted exception chain cannot recover the raw cause text.
- Service tests assert `latest_only` requests the bounded five-value window and
  persists only the maximum valid observation with matching same-year GDP
  context.
- Service tests assert World Bank targets map to existing Buffett codes, dry-run writes nothing, skipped rows produce diagnostics, stored components satisfy source/method metadata, GDP context is included when available, and invalid target codes roll back.
- Script tests assert dry-run output, `--no-latest-only`, bad year parsing, and provider failures.
- Source-readiness tests assert the World Bank adapter item appears, remains guidance-only without observations, and becomes configured only from local observations.
- Dashboard/API tests assert source gaps update additively and citation lists do not include readiness IDs or template IDs.

### 7. Wrong vs Correct

#### Wrong

```python
upsert_market_indicator_observation(
    MarketIndicatorObservationSeed(
        code="buffett_indicator_us",
        as_of=date(2024, 12, 31),
        value=Decimal("0"),
        source="World Bank",
        components={"source_url": "https://data.worldbank.org/indicator/CM.MKT.LCAP.GD.ZS"},
    ),
    session=session,
)
```

This stores a missing or placeholder value and lacks method metadata, so AI could cite a fabricated macro fact.

#### Correct

```python
refresh_world_bank_macro_indicators(
    session=session,
    target_group="USA",
    latest_only=True,
    dry_run=False,
)
```

The refresh path fetches official World Bank rows, skips missing values, preserves source and methodology metadata, validates indicator codes, and writes only audited observations.
