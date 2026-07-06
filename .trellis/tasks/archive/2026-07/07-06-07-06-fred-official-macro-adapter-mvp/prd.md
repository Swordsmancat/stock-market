# FRED Official Macro Adapter MVP

## Goal

Implement a source-auditable FRED macro adapter MVP for core US rates, inflation, and liquidity observations so dashboard AI summaries can cite validated local macro evidence instead of relying only on manual seed templates.

## Background

The platform now has:

- Macro indicator definitions for `us_10y_yield`, `us_2y_yield`, `us_10y_2y_spread`, `us_cpi_yoy`, and `us_m2_yoy`.
- `MarketIndicatorObservation` persistence with audited `source`, `as_of`, and `components`.
- Manual JSON/CSV seed import and source-to-seed templates.
- Dashboard AI summaries that may cite stored macro observations but must not cite source-readiness links or templates.

The next product step is to connect a small official macro source adapter. FRED is a good first adapter because it provides documented API access to US macro series through `fred/series/observations`.

## Requirements

### R1. FRED Source Configuration

- Add explicit FRED configuration to application settings:
  - API key from environment, e.g. `FRED_API_KEY`.
  - API base URL with safe default, e.g. `https://api.stlouisfed.org/fred`.
- If the API key is missing, the adapter must return a clear degraded/no-data result and must not attempt anonymous or hardcoded credentials.
- Do not log or expose the API key in diagnostics, exceptions, or dashboard payloads.

### R2. FRED Observation Adapter

- Add a FRED adapter for observation series, scoped to official FRED API responses.
- Initial target mappings:
  - `DGS10` -> `us_10y_yield`
  - `DGS2` -> `us_2y_yield`
  - `T10Y2Y` -> `us_10y_2y_spread`
  - `CPIAUCSL` -> `us_cpi_yoy` via YoY derivation if no direct YoY target is selected
  - `M2SL` -> `us_m2_yoy` via YoY derivation if no direct YoY target is selected
- Parse missing FRED values such as `"."` as no observation, not zero.
- Preserve source metadata:
  - `source_series_id`
  - `source_url`
  - `retrieved_at`
  - `frequency` / `units` if returned or requested
  - `methodology` or `calculation`

### R3. Import Into Existing Macro Evidence Layer

- Reuse existing `MarketIndicatorObservationSeed` and `upsert_market_indicator_observation(...)` path.
- Seed definitions before validating/writing observations.
- Validate all fetched/derived observations before writing to avoid partial bad imports.
- Store only observations whose value and audit metadata pass the existing seed-import contract.

### R4. CLI / Maintenance Entry Point

- Add a local maintenance command to refresh FRED macro observations.
- The command should support:
  - target group or all configured FRED series.
  - start/end dates or latest-only mode.
  - dry-run mode.
  - clear output explaining inserted/updated observations and skipped no-data points.
- The command must not run automatically in this MVP.

### R5. Dashboard / AI Citation Boundary

- Dashboard macro indicators and AI brief may cite FRED-derived observations only after they are stored locally.
- Source readiness links and seed templates remain guidance only.
- Missing API key, FRED errors, empty responses, or missing values must show as degraded/no-data diagnostics, not fabricated values.

### R6. Documentation and Tests

- Update README/manual/runbook with FRED setup, command usage, and citation boundary.
- Add focused provider/service/script tests with mocked HTTP responses.
- Tests must not require live FRED network access or a real API key.

## Acceptance Criteria

- [ ] FRED API key/base URL settings exist and secrets are not surfaced.
- [ ] FRED adapter parses mocked `series/observations` JSON for rates, spread, CPI, and M2.
- [ ] Missing FRED values are skipped without writing zero.
- [ ] CPI/M2 YoY derivation uses auditable calculation metadata.
- [ ] Refresh service writes observations through `upsert_market_indicator_observation(...)`.
- [ ] Refresh service is all-or-nothing for invalid rows.
- [ ] CLI supports dry-run and mocked tests.
- [ ] Dashboard macro indicators can cite stored FRED observations while source-readiness templates remain non-citable.
- [ ] README/manual/runbook document setup and boundaries.
- [ ] Focused backend tests pass; full tests pass or unrelated failures are documented.

## References

- FRED API docs: https://fred.stlouisfed.org/docs/api/fred/
- FRED series observations endpoint: https://fred.stlouisfed.org/docs/api/fred/series_observations.html
