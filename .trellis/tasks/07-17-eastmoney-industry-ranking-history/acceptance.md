# Eastmoney Industry Ranking History Acceptance

Date: 2026-07-18 (Asia/Shanghai)

## Runtime

- Docker services: API and Web healthy on `8000` and `3000`; PostgreSQL,
  Redis, Worker and Beat running.
- Bounded public-host refresh: succeeded in 21,220 ms with `stored_count=20`.
- Stored projection: 180 rows, 20 trading days, 9 observed industries, from
  2026-06-22 through 2026-07-17.
- Rank repair: 136 stale derived ranks corrected; zero trading dates retain
  duplicate, missing or gapped ranks.
- Database-only GET: `/sectors/industry-rankings?days=20&limit=20` returned the
  canonical source/taxonomy metadata and all 20 stored trading dates.

The public universe endpoints reported 128 total industries and returned the
bounded first 100. Public history availability remains intermittent in the
current network. The successful run used the permitted host sequence without
Cookie, proxy, account login or browser state. A later all-empty run failed
with `EASTMONEY_INDUSTRY_SCHEMA_REJECTED` and preserved all 180 rows, proving
that HTTP 200 empty payloads no longer create a false successful refresh.

## Quality Gates

- Backend: `1149 passed`.
- Frontend: `433 passed` across 118 files.
- TypeScript: passed with `--noEmit`.
- Ruff: passed for `apps`, `packages`, `tests`, `scripts` and `alembic`.
- Focused industry/provider/service/API/worker suite: `33 passed`.
- API health and `/zh/market-research`: HTTP 200.

## Safety

No upstream body, Cookie, proxy value, credential URL, authorization header,
environment dump or exception stack is stored in this artifact. Existing
failed TaskRuns remain available as sanitized operational evidence.
