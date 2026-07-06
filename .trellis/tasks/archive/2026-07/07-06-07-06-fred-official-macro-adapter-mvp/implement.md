# Implementation Plan

## Pre-Development

- [x] Create Trellis task after user confirmation.
- [x] Review current macro indicator persistence and provider/config patterns.
- [x] Check official FRED API docs for the observations endpoint.
- [x] Read backend specs and shared guides before code edits.

## Step 1: Configuration and Provider

- [x] Add FRED settings to `packages/shared/config.py`.
- [x] Create `packages/providers/fred_provider.py` with injected HTTP getter.
- [x] Parse `fred/series/observations` JSON into typed rows.
- [x] Sanitize missing API key, HTTP, and malformed payload errors.
- [x] Add provider tests for direct values, missing `"."`, malformed values, and API-key sanitization.

## Step 2: Refresh Service

- [x] Add FRED target mapping for rates, spread, CPI YoY, and M2 YoY.
- [x] Build direct observation seeds for rates/spread.
- [x] Build derived YoY seeds for CPI and M2 with calculation metadata.
- [x] Validate all candidate seeds before writing.
- [x] Reuse `upsert_market_indicator_observation(...)`.
- [x] Add service tests for all-or-nothing behavior, derivation, and skipped missing rows.

## Step 3: CLI

- [x] Add `scripts/refresh_fred_macro_indicators.py`.
- [x] Support `--series`, `--start`, `--end`, `--latest-only`, and `--dry-run`.
- [x] Print readable OK/WARN/FAIL output without leaking API keys.
- [x] Add script tests with mocked settings/provider/service.

## Step 4: Docs

- [x] Update README with FRED setup and command.
- [x] Update `docs/manual/user-guide.md` with official adapter behavior and boundary.
- [x] Update developer maintenance runbook with FRED refresh troubleshooting.
- [x] Update backend spec for official macro adapter source contract if useful.

## Validation

Focused checks:

```powershell
pytest tests/providers/test_fred_provider.py tests/services/test_market_indicators_fred_refresh.py tests/scripts/test_refresh_fred_macro_indicators.py tests/services/test_market_indicators_service.py tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py
ruff check packages/providers/fred_provider.py packages/services/market_indicators.py scripts/refresh_fred_macro_indicators.py tests/providers/test_fred_provider.py tests/services/test_market_indicators_fred_refresh.py tests/scripts/test_refresh_fred_macro_indicators.py
```

Full checks:

```powershell
pytest
npm run test:web -- --reporter=dot
git diff --check
```

## Review Gate

- [x] Confirm the user wants to start implementation after reviewing PRD/design/implement.

## Risk Points

- No live FRED network calls in tests.
- No API key leakage.
- No fake macro observations.
- No dashboard citation until local observations are stored.
- Do not add automatic scheduled refresh in this MVP.
