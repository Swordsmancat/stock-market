# No-data and provider-error UX contract - Implementation Plan

## Steps

1. Add focused failing tests for report generation with empty bars:
   - service-level typed error;
   - reports API 422 response;
   - analysis sync API 422 response.
2. Add no-data metadata to market-data payloads while preserving successful shapes.
3. Add `ReportDataUnavailableError` and guard `generate_stock_report_payload()` before indexing bars.
4. Map the typed error in report and analysis routers.
5. Run focused backend validation.

## Validation

```powershell
python -m pytest tests/services/test_market_data_service.py tests/api/test_market_data_api.py -v
python -m pytest tests/services/test_report_service.py tests/api/test_reports_api.py tests/api/test_analysis_api.py -v
```

## Stop points

Pause if implementation requires:

- changing existing successful payload field names;
- exposing provider original exception text;
- database schema migration;
- frontend redesign beyond adding localized strings in a later UI task.
