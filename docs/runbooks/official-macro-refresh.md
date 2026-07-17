# Official Macro Indicator Refresh Runbook

This runbook is for manual, opt-in refreshes of official macro observations used by the homepage macro favorites, Macro Research, saved research briefs, and AI summaries.

The complete indicator-to-source/field registry and provider replacement procedure is documented in [Macro data sources](./macro-data-sources.md).

The refresh scripts store audited local `MarketIndicatorObservation` rows. Source-readiness links, seed templates, probe URLs, and script diagnostics are guidance only; AI summaries may cite macro values only after observations are stored locally with source and method metadata.

## Scope

Covered in the current refresh path:

- AkShare public China macro adapter backed by identified Eastmoney/Jin10 pages:
  - LPR 1Y/5Y, SHIBOR overnight, China/US 10Y yields;
  - China CPI/PPI, retail sales, manufacturing PMI, GDP;
  - exports/imports, M2/M1/M0, and national tax revenue.

- FRED US rates and liquidity context:
  - `DGS10` -> `us_10y_yield`
  - `DGS2` -> `us_2y_yield`
  - `T10Y2Y` -> `us_10y_2y_spread`
  - `CPIAUCSL` -> `us_cpi_yoy`
  - `M2SL` -> `us_m2_yoy`
- World Bank Buffett Indicator observations:
  - `USA` + `CM.MKT.LCAP.GD.ZS` -> `buffett_indicator_us`
  - `CHN` + `CM.MKT.LCAP.GD.ZS` -> `buffett_indicator_cn`
  - `HKG` + `CM.MKT.LCAP.GD.ZS` -> `buffett_indicator_hk`

Not covered in this runbook:

- Direct NBS/PBOC production adapters; the current China monthly adapter uses AkShare with the upstream page recorded per observation.
- Scheduled background refresh jobs.
- Automatic refresh on page GET. The browser refresh button is an explicit mutation and uses the API below.
- Scraping public websites or storing raw licensed documents.
- Trading recommendations, buy/sell/hold calls, target prices, sizing, or execution instructions.

## Prerequisites

Run from the repository root:

```powershell
cd "E:\stock market"
```

Apply database migrations before writing observations:

```powershell
alembic upgrade head
```

FRED requires an API key:

```powershell
$env:FRED_API_KEY="..."
```

Optional base URL overrides:

```powershell
$env:FRED_API_BASE_URL="https://api.stlouisfed.org/fred"
$env:WORLD_BANK_API_BASE_URL="https://api.worldbank.org/v2"
```

World Bank refresh does not require a secret.

## AkShare China Macro Refresh

The browser button calls this explicit endpoint:

```text
POST /market-indicators/official-refresh/akshare-cn
{"dry_run": false, "history_limit": 12}
```

Expected behavior:

- Each provider family is isolated; one schema/provider failure does not discard successful families.
- Successful observations are audited and upserted into `MarketIndicatorObservation`.
- The response includes bounded family statuses and sanitized diagnostics.
- `dry_run=true` validates and rolls back all writes.
- Opening or reloading `/evidence` never calls AkShare.

## FRED Refresh

Dry-run latest US rates first:

```powershell
python scripts/refresh_fred_macro_indicators.py --series rates --latest-only --dry-run
```

Dry-run all supported FRED macro series:

```powershell
python scripts/refresh_fred_macro_indicators.py --series all --latest-only --dry-run
```

Write latest supported observations:

```powershell
python scripts/refresh_fred_macro_indicators.py --series all --latest-only
```

Write a date range:

```powershell
python scripts/refresh_fred_macro_indicators.py --series all --start 2025-01-01 --end 2026-07-06
```

Expected behavior:

- Missing `FRED_API_KEY` prints a sanitized `WARN` and writes nothing.
- Provider or validation failures print `FAIL` and avoid leaking secrets.
- Missing FRED values such as `"."` are skipped, not stored as zero.
- CPI/M2 YoY values are derived only when the current and prior-year values are both valid.

## World Bank Buffett Indicator Refresh

Dry-run one region:

```powershell
python scripts/refresh_world_bank_macro_indicators.py --target USA --dry-run
```

Write the latest supported regions:

```powershell
python scripts/refresh_world_bank_macro_indicators.py --target all
```

Write a historical range for one indicator:

```powershell
python scripts/refresh_world_bank_macro_indicators.py --target buffett_indicator_us --start-year 2020 --end-year 2024 --no-latest-only
```

Expected behavior:

- Annual World Bank data is naturally lagged and should not be described as realtime market data.
- Missing, null, blank, non-decimal, or non-finite rows are skipped, not stored as zero.
- GDP context from `NY.GDP.MKTP.CD` is stored as component metadata when available.
- `--dry-run` fetches and validates rows, then rolls back so no observations remain.

## Verify Results

Run focused backend checks:

```powershell
pytest tests/providers/test_fred_provider.py tests/providers/test_world_bank_provider.py tests/services/test_market_indicators_fred_refresh.py tests/services/test_market_indicators_world_bank_refresh.py tests/scripts/test_refresh_fred_macro_indicators.py tests/scripts/test_refresh_world_bank_macro_indicators.py -q
```

Run dashboard and citation-boundary checks:

```powershell
pytest tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py -q
```

After writing observations, verify the UI:

1. Start the API and web app.
2. Open the homepage and check followed macro indicators.
3. Open `/evidence` and check Macro Research.
4. Confirm refreshed rows show value, as-of date, source, and source/method metadata.
5. Confirm unsupported values such as `cn_m2_yoy` remain explicit source gaps.
6. Confirm source-readiness IDs, seed-template IDs, and collection links do not appear as AI citations.

## Troubleshooting

| Symptom | Meaning | Next action |
|---|---|---|
| `WARN FRED refresh: FRED API key is not configured.` | FRED secret is missing. | Set `FRED_API_KEY` and rerun. |
| FRED writes no CPI/M2 YoY row | Current or prior-year source value is missing or invalid. | Rerun with a date range that includes both periods. |
| World Bank latest year is older than expected | Annual public data is lagged. | Treat it as as-of annual context, not realtime market data. |
| Homepage still shows a gap after refresh | No local observation exists for that indicator, or the API cache/page needs refresh. | Recheck script output, restart or refresh the API/web app, then open `/evidence`. |
| AI summary does not cite a source-readiness link | Correct behavior. | Only stored local observations are citable macro evidence. |
