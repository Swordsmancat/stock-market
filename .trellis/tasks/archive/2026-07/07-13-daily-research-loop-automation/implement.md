# Daily research loop automation - implementation plan

## 1. Lock shared evidence and lineage contracts

- Add focused tests for the shared completed-bar SQL/Python predicate and move
  the existing outcome implementation without changing behavior.
- Add model and migration tests for nullable
  `ResearchShortlistRun.generation_task_run_id`, its index, foreign key, and
  `ON DELETE SET NULL` upgrade/downgrade behavior.
- Extend shortlist generation tests first for internal exact-date cutoff,
  original TaskRun lineage, reuse without overwrite, invalid UUID, and public
  API inability to supply either internal field.
- Extend outcome serialization tests for terminal evaluation lineage and null
  derived-pending lineage.

## 2. Implement trusted daily-bar watermark

- Publicize the active CN/AkShare backfill read helper.
- Implement a local-only watermark resolver using eligible finished full-scope
  backfill ranges, active CN stock scope, the shared completion predicate,
  exact-date 95% coverage, and SSE/SZSE/BSE representation.
- Cover no-data, not-ready, threshold boundary, partial full-scope success,
  excluded run kinds/statuses, weekends, pre/post 16:00, future dates, naive
  SQLite UTC, latest eligible provenance, and no provider calls.
- Keep query count bounded as fixture universe size grows.

## 3. Implement due-cohort batching

- Add three literal Nth-completed-bar probes for missing 5/20/60 terminal rows,
  union them into one oldest-first run selector, and avoid full-history counts.
- Add second-priority benchmark-due selection only when canonical exact entry
  and maturity bars can progress the row.
- Enforce deterministic oldest-first ordering and run limit `1..100`.
- Call the existing evaluator per run with verified cutoff and TaskRun ID;
  rollback/record/continue isolated failures.
- Bound canonical benchmark loading to required exact entry/maturity dates and
  return `has_more` from a sentinel instead of an offset cursor.
- Test multiple old cohorts, different maturity horizons, candidate priority,
  benchmark no-op exclusion and one-time enrichment, inactive candidates,
  bounded failure records, repeated/concurrent idempotency, and no provider
  access.

## 4. Implement orchestration and worker

- Add `DailyResearchLoopInput` normalization and result contract.
- Implement active/watermark deferred results, due-outcome phase, exact-date
  generation/reuse, publication readiness degradation, safety flags, progress,
  and partial-failure classification.
- Add the Celery wrapper with direct-Beat TaskRun creation, supplied TaskRun
  reuse, progress heartbeat, partial-result persistence, fail/re-raise, and
  guaranteed session close.
- Add dispatch registry and synchronous test helper support.
- Add settings, `.env.example` documentation, Celery import, and configurable
  weekday 21:30 Beat entry.
- Align read-only TaskRun health stale detection with heartbeat fallback.

## 5. Verification

Run focused checks while implementing:

```powershell
python -m pytest tests/services/test_daily_bar_completion.py tests/services/test_research_evidence_backfill.py -q
python -m pytest tests/services/test_research_shortlists.py tests/services/test_research_shortlist_outcomes.py tests/services/test_daily_research_loop.py -q
python -m pytest tests/domain/test_models.py tests/domain/test_migrations.py tests/api/test_research_shortlists_api.py tests/api/test_research_shortlist_outcomes_api.py -q
python -m pytest tests/worker/test_tasks.py tests/worker/test_celery_schedule.py tests/services/test_task_runs_service.py tests/scripts/test_task_run_health.py -q
python -m ruff check packages/domain/models.py packages/services apps/worker scripts/task_run_health.py alembic/versions/0022_research_shortlist_task_run.py tests
```

Then run the full affected-repository gate:

```powershell
python -m pytest -q
npm run test:web
npx tsc --noEmit -p apps/web/tsconfig.json
python -m json.tool apps/web/messages/en.json > $null
python -m json.tool apps/web/messages/zh.json > $null
alembic heads
alembic upgrade head
alembic downgrade 0021_research_shortlist_outcomes
alembic upgrade head
python ./.trellis/scripts/task.py validate 07-13-daily-research-loop-automation
git diff --check
```

- Run Trellis Check across backend service/domain/worker/config/script layers.
- Verify normal `http://127.0.0.1:3000` and `http://127.0.0.1:8000` remain
  healthy; exercise one local/synthetic synchronous loop twice to prove domain
  reuse without network access.
- If PostgreSQL is available, verify migration `0022` and the advisory-lock
  paths there as well as SQLite-focused tests.

## Rollback points

- After step 1: downgrade/remove only the nullable lineage column; existing
  research data remains.
- After step 2: disable the loop; manual shortlist/outcome behavior is unchanged.
- After step 3: remove the batch selector; per-run manual evaluation remains.
- After step 4: set `DAILY_RESEARCH_LOOP_ENABLED=false`; TaskRun history and
  committed domain rows remain auditable.

## Verification Record - 2026-07-13

- Full backend: `783 passed`.
- Full frontend: `234 passed`; TypeScript and both locale JSON files passed.
- Touched-file Ruff, Trellis context validation, and `git diff --check` passed.
  Repository-wide Ruff still has unrelated pre-existing unused imports outside
  this task's changed files.
- Normal PostgreSQL is at `0022_research_shortlist_task_run (head)`. A fresh
  isolated PostgreSQL database completed full upgrade, downgrade to
  `0021_research_shortlist_outcomes`, and re-upgrade to `0022`, then was
  deleted.
- API port 8000 and AI Research page on port 3000 are healthy. Celery connects
  to Redis and registers 25 tasks, including
  `research.run_daily_research_loop`.
- Real Celery TaskRun `41e7f041-a700-4e05-ae7d-ec29f96c8888` succeeded with an
  expected `deferred` result and final progress `3/3`; the development database
  had only `2/3` exact-date coverage and `UNKNOWN` exchange attribution, so no
  provider/LLM call or shortlist/outcome mutation occurred.
- `test_daily_research_loop_integration.py` exercises the unmocked ready path
  twice over one synthetic database: the first run resolves 3/3 exchange
  coverage, matures one 5-session outcome, and creates a three-item shortlist;
  the second performs zero due work and reuses the same shortlist and original
  TaskRun lineage without revising the terminal outcome.
- Independent implementation and spec reviews reported no remaining P0-P2
  functional findings after schedule configuration, TaskRun takeover, and
  twice-run integration regressions were added.
