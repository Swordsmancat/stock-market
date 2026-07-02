# Add Client Interaction Coverage Design

## Scope

This task adds focused Vitest + Testing Library coverage for `GenerateDailyReportButton`. It does not change runtime component behavior unless tests expose an existing bug.

## Target Component

- Component: `apps/web/components/generate-daily-report-button.tsx`
- Existing behavior:
  - renders a localized generate button;
  - calls `/api/reports/<encoded-symbol>/daily/generate?start=<start>&end=<end>` with `POST`;
  - shows generating state while pending;
  - shows success/failure feedback;
  - calls `router.refresh()` after success.

## Test Strategy

- Mock `next/navigation` router and assert `refresh()` calls.
- Mock `next-intl` translations with stable English labels.
- Mock `fetch` directly with controllable promises for loading state assertions.
- Use Testing Library user interactions and visible text assertions.
- Restore mocks between tests.

## Compatibility

- No backend contract changes.
- No translation catalog changes expected.
- Existing report proxy route tests remain the network-forwarding coverage; this task covers browser-side interaction behavior.
