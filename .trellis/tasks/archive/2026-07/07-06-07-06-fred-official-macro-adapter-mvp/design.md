# Design: FRED Official Macro Adapter MVP

## Boundary

This task adds an explicit, opt-in FRED macro observation refresh path. It does not add automatic scheduled refresh, broad macro provider abstraction, charting changes, or AI prompt changes. AI and dashboard citations still come only from persisted local `MarketIndicatorObservation` rows.

## Proposed Files

- `packages/shared/config.py`
  - Add `fred_api_key: str | None = None`.
  - Add `fred_api_base_url: str = "https://api.stlouisfed.org/fred"`.
- `packages/providers/fred_provider.py`
  - Official FRED observation client with dependency-injected HTTP getter for tests.
  - Returns typed observation rows and safe diagnostics.
- `packages/services/market_indicators.py`
  - Add FRED refresh mapping/service helpers, or delegate to a new service if the file grows too much.
  - Reuse `MarketIndicatorObservationSeed` and existing validation/upsert functions.
- `scripts/refresh_fred_macro_indicators.py`
  - Local maintenance entry point, no automatic scheduling.
- Tests:
  - `tests/providers/test_fred_provider.py`
  - `tests/services/test_market_indicators_fred_refresh.py`
  - `tests/scripts/test_refresh_fred_macro_indicators.py`

## Data Flow

```text
CLI command
  -> refresh service
  -> FRED provider fetches series observations with API key
  -> provider normalizes raw rows and skips missing "."
  -> service maps/derives target indicator observations
  -> service validates audit metadata
  -> upsert_market_indicator_observation(...)
  -> dashboard existing macro payload / brief citations
```

## FRED Provider Contract

Provider input:

- `series_id`
- `observation_start`
- `observation_end`
- optional `frequency`
- optional `units`

Provider output row:

- `series_id`
- `date`
- `value: Decimal | None`
- `raw_value`
- `realtime_start`
- `realtime_end`

Provider behavior:

- Use `fred_api_key`; if missing, raise/return a sanitized unavailable diagnostic at the service boundary.
- Request JSON format.
- Treat `"."`, empty string, missing `value`, invalid decimal, or missing date as skipped rows with diagnostics.
- Do not retry aggressively in this MVP.
- Do not leak full query URL if it contains `api_key`.

## Target Series Mapping

| FRED series | Target code | Handling |
|---|---|---|
| `DGS10` | `us_10y_yield` | Direct decimal percent value. |
| `DGS2` | `us_2y_yield` | Direct decimal percent value. |
| `T10Y2Y` | `us_10y_2y_spread` | Direct decimal percent spread. |
| `CPIAUCSL` | `us_cpi_yoy` | Derive YoY percent from same month one year earlier. |
| `M2SL` | `us_m2_yoy` | Derive YoY percent from same month one year earlier. |

YoY calculation:

```text
((current_value / prior_year_value) - 1) * 100
```

Skip derivation when current/prior values are missing or prior value is zero. Store calculation metadata in `components`.

## Persistence Contract

Each persisted observation uses:

- `source`: `FRED <series_id>` or `FRED <series_id> derived YoY`.
- `components.source_series_id`
- `components.source_url`
- `components.retrieved_at`
- `components.methodology` or `components.calculation`
- `components.provider = "fred"`
- `components.raw_series_id`
- for derived indicators: `current_value`, `prior_year_value`, `formula`, `source_observation_dates`

The refresh service should build all candidate seeds, validate them against the existing seed contract and known indicator codes, then write in one transaction.

## CLI Shape

```powershell
python scripts/refresh_fred_macro_indicators.py --series all --start 2025-01-01 --end 2026-07-06 --dry-run
python scripts/refresh_fred_macro_indicators.py --series rates --latest-only
```

Expected output:

- `OK` with counts for fetched, skipped, inserted/updated.
- `WARN` when API key is missing or series returns no usable observations.
- `FAIL` for malformed provider responses or validation failures.

## Dashboard and AI Behavior

No dashboard code should need to special-case FRED. Once observations are stored, existing macro indicator and dashboard brief logic can cite them. If no observations are stored, current no-data/source-readiness behavior remains unchanged.

## Risks

- FRED units/frequency choices can change interpretation. Store request units/frequency and methodology.
- CPI/M2 are monthly while rates are daily. Do not force daily interpolation.
- API key leakage through exception strings is easy. Sanitize provider errors.
- Backfilling too many observations may create noise. MVP can default to latest-only or a small configured date window.

## Rollback

Because persistence uses existing macro observation upserts, rollback can be done by removing the script/provider/service code and deleting any locally imported FRED observations if needed. Dashboard no-data behavior remains safe when observations are absent.
