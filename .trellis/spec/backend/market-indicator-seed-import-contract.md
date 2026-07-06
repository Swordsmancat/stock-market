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
