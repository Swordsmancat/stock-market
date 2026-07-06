# Audited Macro Seed Import

## Goal

Add an offline audited seed-file import path for macro and valuation observations so hard-to-find data can be collected manually and summarized by AI without live scraping or fabricated values.

## Background

The revised product direction is a personal investment information aggregation and AI summary site, not a professional trading terminal. The current macro implementation already has:

- curated macro and valuation indicator definitions in `packages/services/market_indicators.py`.
- audited observation storage through `MarketIndicatorObservation`.
- dashboard and source-readiness panels that show `no_data` until observations exist.
- AI daily brief sections that can cite macro observations once they are stored locally.

The remaining gap is operational: a user needs a simple, reviewable way to load values from official/public sources or personal research files after manually checking them.

## Requirements

### R1. Offline Seed File Import

- Support importing macro/valuation observations from local seed files.
- Support JSON and CSV inputs because both are convenient for personal research workflows.
- Do not add live network calls, scraping, provider credentials, or implicit source fetching.
- Reuse the existing `MarketIndicatorObservationSeed` and `upsert_market_indicator_observation()` persistence path.

### R2. Auditable Metadata

- Every imported row must include:
  - `code`
  - `as_of`
  - `value`
  - `source`
  - `components`
- `components` must include at least one source reference field such as `source_url` or `source_series_id`.
- `components` must include at least one review/method field such as `methodology`, `calculation`, or `notes`.
- Import failures must explain the row and field that failed validation.

### R3. Atomic Validation

- Validate all rows before committing any observation.
- Reject unknown indicator codes unless definitions are seeded or already present.
- Reject malformed dates, non-decimal values, empty sources, non-object JSON components, and missing audit fields.
- Preserve the existing no-fabrication boundary: invalid or incomplete rows do not become dashboard data.

### R4. Usable Personal Import Script

- Add a small command-line entry point for importing a reviewed seed file into the configured database.
- The script should print concise status output with imported row count and source path.
- The script is allowed to write data only when the user explicitly runs it.
- Keep output free of secrets or raw credential values.

### R5. Documentation

- Update the README and user manual with the seed file format and import command.
- Describe the feature as a manual/audited collection path, not an official live feed.
- Mention that imported observations become available to macro dashboard/source readiness/AI summaries through the existing database.

## Acceptance Criteria

- [ ] A service helper can parse and validate JSON and CSV seed files into `MarketIndicatorObservationSeed` rows.
- [ ] The import helper validates audit metadata and performs all-or-nothing writes.
- [ ] A script entry point can import a seed file into the configured database and report a concise summary.
- [ ] Focused service tests cover JSON import, CSV import, invalid audit metadata, unknown indicators, and all-or-nothing behavior.
- [ ] Script tests cover success and validation failure without requiring the real configured database.
- [ ] README/manual explain the format, command, and no-live-feed boundary.
- [ ] Focused pytest and ruff checks pass; broader known unrelated lint/type debt remains documented if encountered.

## Out of Scope

- Live FRED/PBOC/SEC adapters.
- Web scraping or automatic content collection.
- New database tables or migrations.
- Investment advice, buy/sell recommendations, or broker/trading workflows.
