# A-share Resumable Evidence Backfill

## Goal

Add a production-safe AkShare-backed pipeline that fills daily bars, latest fundamentals, and derived technical indicators for the complete stored active A-share universe through bounded, observable, resumable work.

## Requirements

- Add durable run state linked to TaskRun, including universe revision, phase, cursor, counts, retry sets, lineage, heartbeat, and cooperative cancellation.
- Preserve existing single-symbol persistence paths and idempotent domain identities.
- Process `daily_bars`, `fundamentals`, and `technical_indicators` as separate phases; local indicator retries must not repeat successful provider fetches.
- Use deterministic `(exchange, symbol)` ordering, a stratified 50-100 symbol canary, five deterministic fundamental shards, default batch size 25, and API bounds of 1-100.
- Baseline bars default to 18 calendar months; incremental bars use a 10-calendar-day overlap.
- First provider is explicitly AkShare. Empty valid data, provider failure, schema failure, timeout/rate limit, insufficient local data, and processing failure remain distinct. No silent fallback is permitted.
- Every in-scope symbol reaches a classified outcome; successful earlier symbols survive later failures.
- Add current evidence coverage by evidence kind and exchange, with gates of 95% bars, 90% critical indicators, 80% critical fundamentals, and non-empty coverage for SSE/SZSE/BSE.
- Add create/get/resume/retry-failed/cancel APIs, worker dispatch, overlap protection, TaskRun progress, Asia/Shanghai scheduling, 18:30 weekday bars/indicators, and daily rotating fundamentals.
- Keep diagnostics sanitized and bounded and preserve research-only/no-trading boundaries.

## Acceptance Criteria

- [ ] Additive ORM/Alembic changes work on PostgreSQL and SQLite-backed tests.
- [ ] TaskRun heartbeat prevents healthy long jobs from expiring while genuinely stale legacy jobs still expire.
- [ ] A partially processed batch can be replayed without duplicate bars, fundamentals, indicators, or lost successes.
- [ ] Resume continues from the stored phase/cursor; retry-failed touches only normalized failed symbols.
- [ ] Cooperative cancellation stops at a checkpoint and preserves accepted evidence.
- [ ] Canary/universe/shard ordering is deterministic across retries.
- [ ] Provider empty/error/schema/timeout/rate-limit states remain distinguishable and never trigger another provider.
- [ ] Coverage reports overall/exchange readiness, freshness, thresholds, latest run, and bounded retry/diagnostic summaries.
- [ ] Duplicate active runs are skipped/reused rather than dispatched twice.
- [ ] Celery schedules use Asia/Shanghai and do not rerun the 18-month baseline.
- [ ] Focused migration, service, provider, API, dispatch, worker, TaskRun, schedule, and query-count tests pass.
- [ ] Touched Ruff, full backend tests, Trellis validation, and `git diff --check` pass before completion.

## Out of Scope

- Web UI, live-network acceptance execution, multi-provider reconciliation, filings/announcements, backtesting, trading, or evidence deletion.
