# Research shortlist outcome tracking - implementation plan

## 1. Domain and migration, test first

- Add model tests for terminal statuses, three allowed horizons, candidate
  cascade, candidate/horizon uniqueness, ratio precision, nullable benchmark
  fields, and relationship behavior.
- Add Alembic `0021` upgrade/downgrade tests for constraints, indexes, foreign
  keys, and SQLite/PostgreSQL-compatible UUID/JSON types.
- Implement `ResearchCandidateOutcome` and the migration only after the focused
  tests fail for the expected missing schema.

## 2. Evaluation and read service, test first

- Build focused fixtures for a committed run, frozen candidates, canonical
  entry bars, forward candidate bars, stock `000300`, and optional canonical
  `cn_csi_300` index bars.
- Cover 4/5, 19/20, 59/60 boundaries; entry exclusion; cutoff exclusion;
  suspensions; N+1 isolation; rising-path and intermediate-low drawdown.
- Cover a prior-day intraday row that remains ineligible after midnight, a
  same-day post-16:00 row, later-date backfill ingestion, naive SQLite timestamp
  normalization, and incomplete frozen entry provenance.
- Cover invalid/zero/negative/OHLC values, entry revision, unknown/mixed
  adjustment, mixed providers with a stable basis, inactive instruments, and
  no provider fallback.
- Correct coordinator provenance for future Tushare `pro.daily` rows, then test
  legacy mislabeled rows normalize to raw and raw/qfq mixed paths block.
- Cover exact-date benchmark entry/exit joins, missing/invalid benchmark states,
  stock/index identity isolation, different maturity dates, and one-way pending
  benchmark enrichment.
- Cover repeated and concurrent evaluation, frozen terminal values after source
  replacement, aggregate identities/null semantics, empty cohorts, pagination,
  and constant query count for a 20-candidate run.
- Use independent sessions to exercise unique-insert conflict recovery and
  conditional benchmark enrichment; races must reload the winner, not return
  an integrity error.
- Include overlapping 5D-versus-60D races and prove one conflicting row cannot
  discard other non-conflicting horizon inserts from the same batch.
- Cover GET with N bars and no terminal row: pending `N/N`,
  `ready_for_evaluation=true`, null ratios, then one terminal row after POST.
- Cover a historical `as_of` before a stored maturity date and prove the
  terminal row is hidden and the earlier pending progress is derived.
- Cover current-local-date rejection, previous-day default, and UTC-to-Shanghai
  date boundaries, including an intraday prior-date row that remains ignored.
- Prove the public API cannot pass a trusted watermark; separately test that the
  internal service accepts a verified current-day watermark only at/after 16:00
  Shanghai time and still rejects incomplete bars.
- Build multi-run history fixtures and prove bounded query count at
  `limit=1`, `limit=10`, and `limit=50`.
- Implement bulk evaluation, serialization, aggregation, conservative completed
  cutoff, run-scoped locking, and stable structured diagnostics.

## 3. FastAPI contract

- Add request/query validation and register tracking before the dynamic run
  route.
- Add evaluate, outcome detail, and tracking API tests for 200 domain states,
  no-data, 400 invalid/future cutoff, 404 run, safety, and nullable values.
- Keep generate/latest/detail response tests unchanged.

## 4. Frontend contract and panel, test first

- Add typed tracking/outcome payload helpers with explicit nullable ratios and
  status unions.
- Add no-store Next proxy tests for tracking, detail, and evaluate, preserving
  upstream body/status/content-type.
- Add component tests for summary counts, pending progress, evaluated and
  benchmark-missing results, localized blocked/unknown codes, update success and
  failure, no-data, and research-only safety.
- Add the panel to the AI Research page as an optional server load after the
  shortlist and before the desk. Prove outcome failure does not affect either.
- Key/remount or synchronize the panel by run ID, and add a sibling/page
  regression proving a shortlist generation refresh cannot retain the prior
  cohort's outcome state.
- Add English/Chinese messages and test that opposite-language backend prose is
  never rendered.

## 5. Verification and review

Run focused checks throughout, then the full affected-layer gate:

```powershell
python -m pytest tests/domain/test_models.py tests/domain/test_migrations.py tests/services/test_daily_bar_sources.py tests/services/test_research_shortlist_outcomes.py tests/api/test_research_shortlist_outcomes_api.py -q
python -m ruff check packages/domain/models.py packages/services/ingestion.py packages/services/research_shortlist_outcomes.py apps/api/routers/research_shortlists.py alembic/versions/0021_research_shortlist_outcomes.py tests/services/test_daily_bar_sources.py tests/services/test_research_shortlist_outcomes.py tests/api/test_research_shortlist_outcomes_api.py
npx tsc --noEmit -p apps/web/tsconfig.json
npm run test:web -- --run apps/web/components/research-shortlist-outcome-panel.test.tsx
python -m pytest -q
npm run test:web
python -m json.tool apps/web/messages/en.json > $null
python -m json.tool apps/web/messages/zh.json > $null
alembic heads
python ./.trellis/scripts/task.py validate 07-13-research-shortlist-outcome-tracking
git diff --check
```

- Run Trellis Check for spec compliance, cross-layer data flow, query behavior,
  safety, and existing-contract compatibility.
- Independently review backend outcome semantics and frontend localization/
  responsive states.
- Browser-test desktop and 390x844 mobile layouts against the local app while
  keeping the normal 3000/8000 services healthy.
- If a reusable outcome contract or qfq limitation is learned, update the
  backend spec before commit.

## Rollback points

- Schema: downgrade `0021`; existing shortlist snapshots remain untouched.
- Backend: remove outcome routes/service; generate/latest/detail continue.
- Frontend: remove outcome panel/proxies; daily shortlist and AI Desk continue.
- Benchmark: missing canonical index data is an accepted null state and must not
  trigger a provider integration inside this task.
