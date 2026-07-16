# Homepage initial data, layout, and localization acceptance

## Automated checks

- Focused homepage: 24/24 passed.
- Full frontend: 94 files, 367 tests passed.
- TypeScript: `npx tsc --noEmit -p apps/web/tsconfig.json` passed.
- English and Chinese translation catalogs parsed as JSON.
- Trellis context validation and `git diff --check` passed.
- No debug logging was added.

## Runtime checks

- Normal Web `http://127.0.0.1:3000/zh`: HTTP 200.
- Normal API `http://127.0.0.1:8000/health`: HTTP 200.
- Chinese homepage rendered stored macro values `224.04%` and `79.54%`
  without the market-overview failure banner.
- Visible homepage text contained localized macro labels and no canonical
  English macro names or raw built-in codes.
- Browser console contained no warning or error entries.

## Responsive checks

| Viewport | Result |
|---|---|
| 1440x1000 | 6 panels, 2 columns, 3 rows, no overlap/overflow; content reaches beyond viewport bottom |
| 1920x1080 | 6 panels, 2 columns, 3 rows, no overlap/overflow; last row ends 18 px above main bottom |
| 1280x720 | Macro/news/fund regions are focusable `overflow-y:auto`; news and fund wheel movement changed only their own scroll position |
| 390x844 | 6 panels, 1 column, 6 rows, no overlap or horizontal overflow; final panel clears fixed mobile navigation |

## Boundaries preserved

- Homepage remains GET-only.
- Other optional reads retain the five-second timeout.
- No backend evidence name, cache TTL, provider, database, or refresh behavior
  changed.
