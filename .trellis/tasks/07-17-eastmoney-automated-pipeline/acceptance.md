# Eastmoney Automated Pipeline Acceptance

Date: 2026-07-18 (Asia/Shanghai)

## Runtime

- Docker services: API and Web healthy on `8000` and `3000`; PostgreSQL,
  Redis, Worker, and Beat running.
- Migration: `0026_industry_daily_rankings` upgraded to
  `0027_fundamental_company_metadata`.
- Worker registration: all four stable Eastmoney task names present.
- Beat registration: all four Eastmoney schedule names present.
- Crawler monitor: 11 total, 11 healthy, 0 attention.

## Bounded Live Runs

| Pipeline | Terminal state | Duration | Stored evidence |
| --- | --- | --- | --- |
| Economic calendar | succeeded | bounded live run | 1,230 events in the requested window |
| Industry ranking history | succeeded | bounded live run | 60 rows across 20 requested days |
| Research news | succeeded | 10,596 ms | 10/10 symbols returned only already-stored articles (`skipped`), with zero provider-empty symbols |
| Research fundamentals | succeeded | bounded live run | 10 snapshots and 10 company metadata rows |

The first two industry attempts failed before persistence because the canonical
public hosts disconnected in the current network. Their failed TaskRuns remain
as evidence and no partial rows were written. The provider now performs a
bounded direct fallback to Eastmoney's public `push2delay` host; the final run
succeeded without Cookie, proxy, login, browser state, or relaxed validation.

## Quality Gates

- Backend: `1146 passed`.
- Frontend: `433 passed` across 118 files.
- TypeScript: passed with `--noEmit`.
- Full backend Python Ruff baseline: passed.
- `git diff --check`: passed (line-ending notices only).
- Trellis task validation: passed.
- Runtime API health and `/zh/crawler-monitor`: HTTP 200.

The final bounded news rerun verified the idempotent status contract:
provider items that are all already stored count as `skipped`, while `empty`
is reserved for a genuinely empty provider response.

## Safety

No upstream response body, prompt, credential, Cookie, proxy value,
authorization header, environment dump, or exception stack is stored in this
acceptance artifact or exposed by the monitor.
