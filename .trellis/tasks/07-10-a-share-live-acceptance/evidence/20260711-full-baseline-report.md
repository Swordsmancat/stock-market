# A-share Full-Market Live Acceptance Report

- Execution window: 2026-07-10 15:04-21:14 UTC
- Runtime: isolated `stock-acceptance` Compose project
- Database: `stock_acceptance`
- Migration head: `0016_daily_bar_provenance`
- Provider / market: `akshare` / `CN`
- Celery timezone: `Asia/Shanghai`
- Daily-bar policy: `cn_resilient`
- Application baseline commits: `435aa8f` through `86fbef3`
- Database writes: isolated acceptance database only

All commands used explicit real-network and acceptance-write guards. Database
connection details, authorization values, cookies, upstream payloads, and raw
exception text are excluded from committed evidence.

## Outcome

The complete 5,530-instrument A-share universe passed all stored-evidence
thresholds without lowering the configured gates.

| Evidence | Ready | Missing | Coverage | Gate | Result |
|---|---:|---:|---:|---:|---|
| Daily bars | 5,508 | 22 | 99.60% | 95% | PASS |
| Technical indicators | 5,514 | 16 | 99.71% | 90% | PASS |
| Fundamentals | 5,523 | 7 | 99.87% | 80% | PASS |

Universe distribution is BSE 327, SSE 2,308, and SZSE 2,895. No exchange is
missing. Daily bars persist explicit provenance: 5,529 instruments and
1,954,561 rows use `akshare.stock_zh_a_daily`. Eastmoney failures opened the
run-local circuit; Tushare remained explicitly unconfigured; no mock, static,
yfinance, or silent provider fallback was used.

## Baseline TaskRuns

| Phase | Backfill run | TaskRun | Attempted | Succeeded | No data / insufficient | Failed |
|---|---|---|---:|---:|---:|---:|
| Daily bars | `2bc917e0-7b45-476c-b314-9146d8923f15` | `08c6bf42-d6eb-43c2-9df2-fbbe568a94b5` | 5,530 | 5,528 | 0 | 2 |
| Indicators | `0991c607-bfb1-4823-8a86-5ec590d50a12` | `0308e118-7243-4c87-ab6a-c854f474f1b0` | 5,530 | 5,517 | 13 | 0 |
| Fundamentals 0/5 | `3ee59c41-8803-4d1e-b415-b6702afb781b` | `4e1b97f5-ae98-4a60-b57b-b6586d0863d1` | 1,106 | 1,105 | 1 | 0 |
| Fundamentals 1/5 | `43a4ed6b-0ae4-49b5-8dd0-e3b56bdc591f` | `c89403b7-f395-4965-b603-660f90ac8636` | 1,106 | 1,105 | 1 | 0 |
| Fundamentals 2/5 | `3d228ca3-1178-44c3-a370-4cf6a9453302` | `122fbaba-677a-49bd-b91d-60d989ded263` | 1,106 | 1,102 | 4 | 0 |
| Fundamentals 3/5 | `db3ff774-e894-4c61-993e-5ad7162c5801` | `4911c0dd-d958-44d1-8fe4-d152486f1e99` | 1,106 | 1,105 | 1 | 0 |
| Fundamentals 4/5 | `eb65f9b1-9e83-4495-bd68-5ade46d054ea` | `a5d04570-7636-4f68-ab21-8a376e6b8299` | 1,106 | 1,106 | 0 | 0 |

The daily-bar run committed every 25 symbols and completed in 5,006,549 ms.
Indicators completed locally in 276,587 ms. Fundamental shards were sequential
and non-overlapping; no second AkShare run was active concurrently.

## Retry and Recovery

`retry-failed` created child run `18e252c2-e583-4d8e-9e43-c85b9e094832`
with TaskRun `708140e7-da49-4daf-a4fe-01ebf395d85e`. It retried the two daily-bar
failures, recovered `300481`, and retained `689009` as a sanitized
`ConnectionError` retry. The remaining gap is an accepted data gap/provider
limitation and does not affect the 95% gate.

The acceptance runner itself initially could not attach to an
`already_running` backfill. Commit `435aa8f` fixed that product defect with
matching-run validation and focused regressions; interrupted runners can now
reattach without mislabeling a different active phase.

## Full-Universe Discovery

Each profile executed twice over unchanged stored evidence. All runs evaluated
5,530 candidates, preserved identical membership/ranking, returned at most 10
symbols, and used the deterministic explanation fallback.

| Profile | Matched | Returned | Stable |
|---|---:|---:|---|
| `balanced_research` | 693 | 10 | PASS |
| `quality_value` | 784 | 10 | PASS |
| `trend_liquidity` | 987 | 10 | PASS |

Discovery reported 5,528 daily-bar, 5,517 indicator, and 5,523 fundamental
records available to screening. LLM use was disabled, so the fixed deterministic
shortlists could not be expanded, reordered, or assigned invented citations.

## Browser Acceptance

- AI Research: PASS at the effective desktop viewport. Coverage gates,
  SSE/SZSE/BSE rows, controlled fallback, source distribution, full-universe
  controls, and the authoritative TaskRun link were visible.
- Evidence Center: PASS. Stored-evidence/citation boundaries and degraded macro
  source states were explicit.
- Final TaskRun: PASS. Inputs, terminal status, counters, safety flags, shard
  identity, and empty diagnostics were visible.
- Console: zero warnings/errors on all three routes.
- Mobile viewport: PENDING ENVIRONMENT RECHECK. The in-app Browser advertised a
  390x844 override but continued reporting a 1280px page viewport. This is
  classified as `environment_configuration`; it is not reported as a product
  pass or failure. Web component tests and TypeScript still pass.

## Finding Classification

| Finding | Classification | Resolution |
|---|---|---|
| Eastmoney reset/provider-wide failures | `provider_limitation` | Explicit Sina fallback selected; provenance retained |
| One persistent symbol bar failure (`689009`) | `accepted_data_gap` | Retry retained; thresholds still pass |
| Runner could not reattach to active backfill | `product_defect` | Fixed and regression-tested in `435aa8f` |
| Mobile viewport override did not change page width | `environment_configuration` | Pending one clean browser-session recheck |
| FRED key and audited macro observations absent | `environment_configuration` | Remains visible and non-citable; outside this A-share baseline |

## Quality Gates

- Backend: 578 tests passed.
- Web: 68 files / 204 tests passed.
- TypeScript `--noEmit`: passed.
- Locale JSON parse: passed.
- Acceptance Compose config: passed.
- Alembic: `0016_daily_bar_provenance (head)`.
- Touched-file Ruff: passed.
- Trellis task validation: passed.
- `git diff --check`: passed before report edits.
- Full-repository Ruff reports 41 pre-existing findings in Trellis support and
  untouched legacy files; no broad out-of-scope cleanup was performed.

## Retention and Operations

The acceptance stack remains running on dedicated ports and retained volumes.
The normal API/Web on ports 8000/3000 remained HTTP 200 throughout. Use the
documented `stock-acceptance` Compose `down` command to stop services while
retaining checkpoints; use `down --volumes` only for separately authorized
destructive cleanup. Resume, retry-failed, cancel, incremental schedules, and
five-way fundamental shards are documented in
`docs/runbooks/a-share-research-coverage.md`.
