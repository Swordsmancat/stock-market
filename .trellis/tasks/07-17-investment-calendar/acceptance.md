# Investment Calendar Acceptance

Date: 2026-07-18 (Asia/Shanghai)

## Runtime

- `GET /investment-calendar` for 2026-07-01 through 2026-07-31 returned
  `status=ok` with 1,161 stored economic events across 28 active days.
- The full month returned `truncated=false`, proving the projection is not
  limited by the legacy 200-row calendar endpoint.
- The localized July page returned HTTP 200 with URL-addressable month, date,
  kind, and importance state.
- Normal page and API reads used stored evidence only and did not contact or
  refresh an external provider.

## Quality Gates

- Focused backend service/API tests: 8 passed.
- Focused frontend helper/page tests: 6 passed.
- Full backend suite: 1146 passed.
- Full frontend suite: 433 passed across 118 files.
- TypeScript `--noEmit`: passed.
- Full backend Python Ruff baseline: passed.
- Trellis validation and `git diff --check`: passed.

## Responsive And Safety

The calendar uses a seven-column month grid with a stacked mobile agenda and
desktop-only navigation entry, covered by the responsive component and
navigation tests. The endpoint is bounded to 42 Shanghai calendar days and
2,500 stored items, exposes truncation explicitly, and never fabricates company
event importance or reads events outside the active CN watchlist scope.
