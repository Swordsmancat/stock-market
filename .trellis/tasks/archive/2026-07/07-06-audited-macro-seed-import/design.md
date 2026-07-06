# Design: Audited Macro Seed Import

## Boundary

This slice turns reviewed local files into `MarketIndicatorObservation` rows. It does not fetch data from the internet. Source authority remains encoded in the file's `source` and `components` fields.

## Seed File Contract

JSON accepts either a top-level array or an object with an `observations` array:

```json
{
  "observations": [
    {
      "code": "us_10y_yield",
      "as_of": "2026-07-03",
      "value": "4.250000",
      "source": "Audited seed: FRED DGS10",
      "components": {
        "source_series_id": "DGS10",
        "source_url": "https://fred.stlouisfed.org/series/DGS10",
        "methodology": "Daily 10-year Treasury constant maturity rate.",
        "notes": "Operator-reviewed seed; not a live feed."
      }
    }
  ]
}
```

CSV uses scalar columns plus `components_json`:

```csv
code,as_of,value,source,components_json
us_10y_yield,2026-07-03,4.250000,Audited seed: FRED DGS10,"{""source_series_id"":""DGS10"",""methodology"":""Daily reviewed value.""}"
```

## Validation Rules

- `code` must be a non-empty string and must exist in `MarketIndicator`.
- `as_of` must parse as ISO date.
- `value` must parse as `Decimal`.
- `source` must be a non-empty string.
- `components` / `components_json` must be a JSON object.
- components must include one of `source_url`, `source_series_id`, `source_document`, `source_name`.
- components must include one of `methodology`, `calculation`, `notes`, `review_note`.

## Service API

Add helpers to `packages/services/market_indicators.py`:

- `parse_market_indicator_observation_seed_file(path) -> list[MarketIndicatorObservationSeed]`
- `import_market_indicator_observation_seed_file(path, session) -> MarketIndicatorSeedImportResult`

The import helper calls `seed_market_indicators()` first so the curated definitions exist, validates every row against the database, then upserts observations with `commit=False` and commits once at the end.

If validation fails, raise `MarketIndicatorSeedImportError` before any observation write. The error message should include row numbers and field-specific reasons.

## Script Entry

Add `scripts/import_market_indicator_seeds.py`.

The script should:

- parse a required seed file path.
- open `SessionLocal()` from `packages.shared.database`.
- call the service import helper.
- print `OK imported <count> macro indicator observations from <path>`.
- print `FAIL seed import: ...` and return nonzero for validation errors.

## Compatibility

- Existing dashboard payloads automatically pick up imported observations through `get_macro_indicator_payloads()`.
- Source readiness automatically sees evidence through existing `MarketIndicatorObservation` queries.
- No schema changes are required.

## Rollback

Because this slice writes normal observation rows, rollback is operational: delete the affected `market_indicator_observations` rows for the imported `code` + `as_of` pairs if a bad file was imported.
