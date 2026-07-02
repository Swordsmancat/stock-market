# Provider settings and readiness visibility

## Goal

Make market-data provider configuration visible, safe, and effective so users can understand which provider is active before attempting data ingestion or display.

This task addresses the first product blocker: users cannot tell whether the app is using `mock`, `yfinance`, `akshare`, or `tushare`, and some routes can unintentionally fall back to `mock` even after platform settings are changed.

## Requirements

- Backend provider selection:
  - Treat an omitted provider query parameter as "use the configured platform default" instead of silently forcing `mock`.
  - Preserve explicit provider query parameters for tests and advanced workflows.
  - Return requested/effective provider names where market-data payloads need user trust.
- Provider capability/readiness metadata:
  - Expose which providers are supported by this build.
  - Distinguish mock data, historical daily-bar providers, and future real-time quote support.
  - Report configuration readiness without requiring real provider network access in default tests.
- Settings safety:
  - Do not expose raw provider secrets such as `tushare_token` in public settings responses.
  - Show whether a secret is configured without revealing the value.
- Frontend visibility:
  - Settings page should display active provider, supported providers, and readiness/capability status.
  - User-facing copy must avoid implying true real-time data when only daily bars are supported.
  - English and Chinese messages must be updated together.

## Acceptance Criteria

- [ ] Public settings responses mask provider secrets while still indicating configuration state.
- [ ] Provider defaults respect platform settings when provider is omitted.
- [ ] Backend exposes enough provider capability/readiness information for the frontend settings page.
- [ ] Settings page shows active provider and provider readiness/capability in both locales.
- [ ] Existing explicit `provider=mock` test workflows still work.
- [ ] No CI test requires live access to yfinance, AkShare, or Tushare.
- [ ] Focused backend and frontend tests cover provider defaulting, secret masking, and settings display.

## Suggested Validation

```powershell
python -m pytest tests/api/test_market_data_api.py tests/services/test_market_data_service.py -v
python -m pytest tests/scripts/test_provider_readiness.py -v
npm run test:web -- "apps/web/app/api/settings/route.test.ts"
```

## Notes

- This task should not introduce a database schema migration.
- This task should not implement true real-time quote fetching.
