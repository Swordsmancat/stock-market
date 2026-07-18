# Crawler Execution Monitor Acceptance

Date: 2026-07-18 (Asia/Shanghai)

## Runtime

- `GET /crawler-monitor` returned the exact eleven curated pipeline IDs.
- Projection summary: 11 total, 0 running, 11 healthy, 0 attention, and 2
  recent failures retained as historical evidence.
- `http://127.0.0.1:3000/zh/crawler-monitor` returned HTTP 200.
- The visible Chinese page showed all eleven rows, localized status/scope/
  cadence labels, bounded progress, and stored TaskRun links.
- The explicit refresh control completed without navigation or mutation and
  the browser console contained no errors.

## Responsive And Theme Review

- The live 1440 x 900 page had no document-level horizontal overflow.
- Both dark and light themes rendered the monitor heading and data without
  horizontal overflow; the default dark theme was restored after review.
- The in-app browser viewport override did not apply to the live tab, so no
  mobile screenshot is claimed. Mobile behavior remains covered by the
  responsive component/navigation tests included in the full frontend suite.

## Quality Gates

- Focused backend monitor tests: 3 passed.
- Focused frontend decoder/refresh tests: 3 passed.
- Full backend suite: 1146 passed.
- Full frontend suite: 433 passed across 118 files.
- TypeScript `--noEmit`: passed.
- Full backend Python Ruff baseline: passed.
- Trellis task validation and `git diff --check`: passed.

## Safety

The monitor performs a bounded database-only read. It does not dispatch,
retry, cancel, expire, or contact providers, and it exposes no raw TaskRun JSON,
credentials, Cookies, proxies, upstream bodies, exception text, or stack
traces.
