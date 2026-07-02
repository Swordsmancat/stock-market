# Provider settings and readiness visibility - Implementation Plan

## Steps

1. Update backend platform settings public payload:
   - mask `tushare_token`;
   - add `tushare_token_configured`;
   - add deterministic market-data provider capability metadata.
2. Update backend market-data provider resolution:
   - omitted provider means platform default;
   - explicit provider still overrides;
   - payloads include requested/effective provider where useful.
3. Update frontend settings data model and settings page:
   - render provider readiness/capability cards;
   - avoid putting raw Tushare token in the password field value;
   - add English and Chinese copy.
4. Update tests for changed provider defaulting and public settings behavior.
5. Run focused validation.

## Validation

```powershell
python -m pytest tests/api/test_market_data_api.py tests/services/test_market_data_service.py -v
python -m pytest tests/scripts/test_provider_readiness.py -v
npm run test:web -- "apps/web/app/api/settings/route.test.ts"
```

## Stop points

Pause if implementation requires:

- real provider network access in tests;
- changing provider credentials storage format;
- database schema migration;
- changing `latest` endpoint semantics from latest daily bar to true quote.
