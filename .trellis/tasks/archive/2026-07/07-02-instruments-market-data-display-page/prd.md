# Instruments market-data display page

## Goal

Add a clear frontend entry point where users can browse instruments and inspect market-data availability, latest daily-bar state, provider/source, freshness, and links to detail/report/task workflows.

This directly addresses the product gap that fetched stock data currently has no obvious display page.

## Requirements

- Add an instruments/market-data page:
  - Create `apps/web/app/[locale]/instruments/page.tsx` or the project-approved equivalent route.
  - Fetch instrument and latest daily-bar data through existing backend/proxy patterns.
  - Use server components for initial data loading unless a specific interaction requires a client component.
- Display useful market-data fields:
  - symbol, name, market, latest close, latest timestamp/as-of, source/provider, and freshness badge.
  - Link each row/card to the instrument detail page.
  - Include follow-up actions or links for refresh/ingestion/report/task-run workflows where available.
- Navigation and empty states:
  - Add the page to desktop/sidebar navigation and mobile navigation where appropriate.
  - Use existing `EmptyState` and `ErrorState` patterns.
  - Guide users to provider settings or ingestion when no data exists.
- Localization and tests:
  - No hardcoded user-visible strings outside locale message files.
  - Add colocated page tests covering success, empty, and failed-load states.

## Acceptance Criteria

- [ ] Users can navigate to a dedicated instruments/market-data page.
- [ ] The page displays instrument identity plus latest daily-bar/source/freshness information.
- [ ] The page clearly distinguishes mock/provider/database source where available.
- [ ] Empty and backend-error states are distinct and actionable.
- [ ] Navigation includes the new page in desktop and mobile entry points as appropriate.
- [ ] English and Chinese locale files are updated together.
- [ ] Colocated frontend tests cover the main rendering branches.

## Suggested Validation

```powershell
npm run test:web -- "apps/web/app/[locale]/instruments/page.test.tsx"
npm run test:web -- "apps/web/app/[locale]/page.test.tsx"
```

## Notes

- This task should not redesign portfolio/watchlist/alert workflows beyond adding links to the new page.
- If backend payloads are insufficient, document the gap and keep changes scoped.
