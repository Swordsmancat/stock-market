# Instruments market-data display page - Implementation Plan

## Scope

Implement the first dedicated market-data browsing page for instruments. Keep the work focused on frontend display, navigation, localization, and tests. Reuse existing backend endpoints and existing latest daily-bar semantics.

## Steps

1. Start the Trellis child task.
2. Add `apps/web/app/[locale]/instruments/page.tsx`.
   - Fetch `/instruments` through `backendFetch`.
   - Fetch platform settings to determine the active provider.
   - Fetch `/market-data/{symbol}/latest` for a bounded list of visible instruments.
   - Render table rows with identity, latest daily close, as-of timestamp, source/provider, freshness, and actions.
3. Add `apps/web/app/[locale]/instruments/page.test.tsx`.
   - Cover successful rows with provider/source/freshness metadata.
   - Cover successful empty instrument list.
   - Cover failed instrument-list load as an error state.
4. Add navigation entries.
   - Desktop sidebar: add `/instruments`.
   - Mobile navigation: add `/instruments` while preserving a usable bottom navigation layout.
5. Add English and Chinese translations.
   - Navigation key for instruments.
   - Page title, description, table headings, freshness labels, empty/error copy, and actions.
6. Run focused validation.
7. Commit, push, archive the Trellis task, and push the archive commit.

## Implementation details

- Limit latest-bar fan-out to a small constant so rendering the initial page does not trigger unbounded backend calls.
- Treat latest-bar failures as row-level unavailable state, not full-page failure.
- Treat failed `/instruments` load as full-page `ErrorState` because the page cannot render its primary list.
- Keep labels honest: use “latest daily bar” / “latest close” copy, not “real-time price”.
- Use localized text for every user-visible label.
- Keep helper functions in the page file because the formatting and freshness rules are page-specific.

## Validation

```powershell
npm run test:web -- "apps/web/app/[locale]/instruments/page.test.tsx"
npm run test:web -- "apps/web/app/[locale]/page.test.tsx"
python ./.trellis/scripts/task.py validate .trellis/tasks/07-02-instruments-market-data-display-page
```
