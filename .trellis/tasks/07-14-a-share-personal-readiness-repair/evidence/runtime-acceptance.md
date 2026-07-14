# Personal A-share readiness runtime acceptance

## Data cleanup

- The guarded transaction matched and deleted exactly nine `600519` daily bars
  where both `provider` and `source` were `legacy_unknown`.
- Post-delete count for that predicate is zero.
- The retained `600519` source is `akshare.stock_zh_a_hist`: 361 rows covering
  2025-01-13 through 2026-07-13.

## Daily bars

- Canary run: `f52b37fd-04aa-44e4-8e02-423f57840e87`.
- Canary result: 49/50 succeeded, retry `000004`, with ready evidence from BSE,
  SSE, and SZSE. The controlled source was predominantly
  `akshare.stock_zh_a_daily` after the primary circuit opened.
- Baseline run: `97c34568-50c2-4a31-bfe1-4db30cffb407`.
- Baseline result: 5,526/5,530 succeeded. The four retries were `689009`,
  `000004`, `002151`, and `002808`, all sanitized `ConnectionError` outcomes;
  no schema or rate-limit diagnostic occurred.
- Ready coverage: 5,508/5,530 (99.6022%). Exchange ready counts are BSE 315,
  SSE 2,305, and SZSE 2,888.

## Indicators and fundamentals

- Technical run: `3d328b35-5252-467f-890b-19690f158f8a`.
- Technical result: 5,516 succeeded, 10 insufficient-history, four no-data,
  zero failed/retry/diagnostics. Ready coverage is 99.7468%.
- Fundamental runs by shard:
  - 0: `8ed79837-9069-4fac-bbd4-d1fa012f7a57`
  - 1: `ecc2b36b-3339-460b-a754-fb04c95e5d20`
  - 2: `128c81dc-f946-4c54-a38c-623bfb4f76af`
  - 3: `daf5a886-e669-4c67-9183-0397cb144d8b`
  - 4: `9b794d76-e904-46a2-8227-cfc877eb86e4`
- Every shard succeeded for 1,106/1,106 symbols with no retry or diagnostic.
  Final fundamental coverage is 5,530/5,530 (100%).

## Daily research loop

- Creation TaskRun: `bb23ac63-fba9-4d43-bce4-0928fe59f6c2`.
- Reuse TaskRun: `9bca494f-c27e-42d5-9640-4d81d044d0f3`.
- Trusted watermark: 2026-07-13, 5,520/5,530 completed bars (99.8192%), with
  BSE/SSE/SZSE representation and no provider/network access in the resolver.
- The first run created ten-item shortlist
  `c0f33ccf-4ccf-44e7-88e0-e74d555d327a`; the second reused the same ID and
  preserved the first TaskRun as `generation_task_run_id`.
- The LLM request failed with a sanitized `HTTPStatusError`; deterministic
  explanation fallback completed without changing shortlist membership or
  ranking.
- Both results retain `research_signal_only=true`,
  `no_automated_trading=true`, and
  `outcomes_do_not_change_shortlist_ranking=true`.

## Quality and health

- Full backend: 786 passed.
- Touched-file Ruff, isolated changed-file mypy, Trellis validation, and
  `git diff --check` passed.
- Repository-transitive mypy remains outside this task's scope with 164
  pre-existing errors across 36 imported files.
- Final evidence coverage status is `ok`; thresholds remain 95/90/80.
- Ports 3000 and 8000 are healthy. A single simultaneous timeout during the
  final shard recovered while the backfill heartbeat continued and did not
  recur under longer double-confirmation checks.
- Final Celery reload: worker PID 33068 and Beat PID 122396. Worker ping and
  registration passed, Redis queue length was zero, and the loaded incremental
  schedule contained `daily_bar_policy=cn_resilient`. The scheduling task
  retained `strict` when the policy kwarg is omitted.
