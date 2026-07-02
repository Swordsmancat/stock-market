# No-data and provider-error UX contract

## Goal

Normalize backend and frontend behavior when providers return no data or fail, so users see actionable product states instead of opaque 500 errors, silent empty screens, or misleading reports.

## Requirements

- Backend error/no-data classification:
  - Distinguish invalid request, unsupported provider/timeframe, provider not configured, provider unavailable, provider returned no data, and internal errors.
  - Sanitize provider exception messages and never expose tokens or secrets.
  - Ensure report/analysis generation handles empty bar collections explicitly.
- API payload behavior:
  - Market-data endpoints should expose no-data outcomes in a stable shape where appropriate.
  - Report/analysis endpoints should return clear errors or task results instead of unhandled `IndexError`/500 behavior.
  - Preserve existing successful response shape where possible.
- Frontend product states:
  - Instrument detail and related market-data displays should show localized empty/error states.
  - Empty states should guide the user toward provider settings, ingestion, or task-run diagnostics.
  - Failed backend requests must render error states, not generic empty states.

## Acceptance Criteria

- [ ] Empty provider bars do not crash report generation with an unhandled exception.
- [ ] Market-data/report/analysis service tests cover no-data and provider failure scenarios.
- [ ] API tests assert sanitized, actionable responses for expected no-data/provider-error cases.
- [ ] Instrument detail frontend tests cover empty and failed market-data loading states.
- [ ] User-visible messages are localized in English and Chinese.
- [ ] No provider token or secret can appear in an API error payload or frontend error message.

## Suggested Validation

```powershell
python -m pytest tests/services/test_market_data_service.py tests/api/test_market_data_api.py -v
python -m pytest tests/services/test_report_service.py tests/api/test_reports_api.py tests/api/test_analysis_api.py -v
npm run test:web -- "apps/web/app/[locale]/instruments/[symbol]/page.test.tsx"
```

## Notes

- Prefer service-boundary normalization over route-level ad-hoc exception handling.
- Do not add real provider network tests.
