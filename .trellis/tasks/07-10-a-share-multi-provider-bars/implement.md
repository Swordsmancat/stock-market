# A-share Multi-Provider Daily-Bar Resilience Plan

## Backend contracts and migration

- [x] Add failing tests for strict policy, fallback ordering, validation, configured-only Tushare, and circuit opening.
- [x] Add normalized daily-bar fetch result/coordinator and AkShare Sina adapter path.
- [x] Add `bars_1d` provenance fields and backfill policy/source-stat fields through Alembic 0016.
- [x] Add priority-aware idempotent persistence tests, including legacy and downgrade protection.

## Backfill, API, and coverage

- [x] Thread `daily_bar_policy` through create/resume/retry, API request, worker result, and serializers.
- [x] Share one coordinator across a backfill execution for pacing and circuit state.
- [x] Persist sanitized per-source counters and preserve retry/no-data semantics.
- [x] Add source/provider distribution to daily-bar coverage without changing thresholds.
- [x] Add focused service, API, worker, coverage, and migration tests.

## AI Research UI

- [x] Make canary/baseline requests explicitly submit `cn_resilient`.
- [x] Render controlled-fallback policy and daily-bar source distribution.
- [x] Update English/Chinese messages and focused component/page tests.

## Validation and rollout

- [x] Run focused and full Python tests, touched Ruff, migration checks, and `git diff --check`.
- [x] Run focused/full Web tests, TypeScript, and locale JSON parsing.
- [x] Run Trellis check and update executable provider/A-share specs.
- [ ] Commit implementation before live network execution.
- [ ] Run read-only source probes and a guarded three-exchange canary; do not start full baseline until the canary is usable.

## Risk and rollback points

- Keep `strict` as the default throughout rollout.
- Do not persist rows that fail normalization/validation.
- Do not let a lower-priority source overwrite a higher-priority canonical row.
- Do not include mock/yfinance in the A-share fallback registry.
- Disable `cn_resilient` callers to roll back behavior without deleting stored evidence.
