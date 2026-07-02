# Add client interaction coverage

## Goal

Add focused frontend client interaction coverage for a high-value user action without changing backend contracts or broad UI behavior.

## Background

Recent work added route-handler proxy tests for task-run retry and daily report generation. The remaining testing backlog still calls out client form or polling behavior coverage. `GenerateDailyReportButton` is a good target because it triggers report generation through the existing daily report proxy, shows loading/success/failure feedback, and refreshes the current route after success.

## Requirements

- Add a focused client interaction test for `apps/web/components/generate-daily-report-button.tsx`.
- Mock network and router boundaries; do not require a live backend service.
- Assert meaningful user-visible behavior: initial label, loading state, success message, failure message, and route refresh on success.
- Do not change backend Python, API contracts, or route proxy behavior.
- Avoid broad UI rewrites or translation changes unless the component itself needs them.

## Acceptance Criteria

- [x] The report generation button sends a `POST` request to the encoded report-generation proxy URL with expected query parameters.
- [x] The button shows a loading/generating state while the request is pending.
- [x] A successful response shows the success message and refreshes the router.
- [x] A failed response shows the failure message and does not refresh the router.
- [x] `npm run test:web` passes.

## Out of Scope

- Changing the daily report generation API route.
- Changing report generation backend behavior.
- Adding browser/E2E tests.
- Reworking report page UI layout.

## Validation

```bash
npm run test:web
```
