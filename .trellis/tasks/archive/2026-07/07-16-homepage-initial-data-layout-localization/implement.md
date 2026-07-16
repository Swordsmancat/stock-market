# Homepage initial data, layout, and localization implementation

## 1. Lock Regressions

- Add a homepage test whose market-overview GET resolves after six seconds and
  assert the real projection renders with no POST.
- Keep/add the terminal failure test for a request that exceeds the new bound.
- Add Chinese success/failure and English macro label assertions, including
  raw-code absence in both locales.

## 2. Implement

- Add the dedicated 20-second market-overview read constant.
- Add built-in macro label translations and the page-local lookup helper.
- Remove homepage macro code subtitles in both locales.
- Change the desktop six-module grid to two columns and three natural rows.

## 3. Verify

- Run focused homepage tests and TypeScript.
- Run the full frontend suite and parse both translation catalogs.
- Run Trellis task validation and `git diff --check`.
- Browser-check 1440x1000, 1920x1080, 1280x720, and 390x844 for first-load data,
  localized macro labels, grid geometry, internal scrolling, overflow, and
  overlap.

## Rollback Points

- If the longer request blocks unrelated optional data, revert only the
  dedicated market-overview constant/use.
- If the two-column desktop grid introduces scrolling or mobile regressions,
  revert only that grid class; localization and timeout remain isolated.
