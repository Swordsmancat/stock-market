# A-share AI research decision loop - implementation plan

## Execution order

### Child 1: persisted daily research shortlist

- Define a versioned, transparent scoring contract over existing local evidence.
- Add shortlist run/candidate models and migration with idempotency and unique
  rank/member constraints.
- Add generation, latest, and detail services/APIs without live provider calls.
- Extend deterministic/LLM explanation inputs with structured factors, opposing
  evidence, gaps, invalidation conditions, and allowed citations.
- Add the latest-shortlist panel to the top of `/ai-research`, preserve manual
  discovery below it, and link candidates to instrument deep analysis.
- Validate service, API, migration, proxy, component, page, localization, lint,
  type-check, full backend, and full frontend suites.

### Child 2: 5/20/60 outcome tracking

- Add candidate outcome persistence and tracking/history APIs.
- Implement direct-DB, exact-trading-day outcome maturation and CSI 300
  date-aligned comparison.
- Add cohort aggregates with pending/evaluated/blocked counts and sample size.
- Surface tracking state and matured results in the daily shortlist workflow.
- Prove no provider fallback, no zero filling, no survivorship deletion, and
  idempotent repeat evaluation.

### Child 3: daily automation and operational acceptance

- Add TaskRun/Celery tasks for shortlist publication and outcome maturation.
- Gate generation on the local A-share daily-bar watermark and schedule after
  evidence ingestion.
- Add retry/idempotency/progress diagnostics and run lineage.
- Exercise manual and scheduled paths against the normal local stack without
  disrupting ports 3000/8000.
- Complete end-to-end parent acceptance and documentation.

## Review gates

Each child must independently complete:

1. PRD/design/implementation review and `task.py start`.
2. Pre-development spec loading.
3. Focused tests and migration validation.
4. Full affected-layer Trellis check.
5. Spec-update judgment, work commit, push, archive, and journal entry.

Do not begin a dependent child until the prior child's published contract and
migration are committed.

## Parent integration validation

```powershell
python -m pytest -q
pnpm --dir apps/web lint
pnpm --dir apps/web typecheck
pnpm --dir apps/web test
python ./.trellis/scripts/task.py validate 07-13-a-share-ai-research-decision-loop
git diff --check
```

Use the repository's actual package scripts if the frontend command names differ.

## Rollback points

- Child 1: remove new panel/routes and downgrade shortlist tables; existing
  discovery remains intact.
- Child 2: disable tracking routes/worker and downgrade outcome tables without
  deleting shortlist snapshots.
- Child 3: disable Beat entries/tasks while preserving manual services and all
  published domain data.

## Final Integration Verification - 2026-07-13

- All three children are completed and archived:
  `7cdef12` persisted daily shortlist snapshots, `282b031` added immutable
  5/20/60 outcome tracking, and `bb7aea9` automated the trusted daily loop.
- Full backend suite: `783 passed`. Full frontend suite: `234 passed`.
  TypeScript, locale JSON, touched-file Ruff, Trellis validation, and
  `git diff --check` passed.
- Normal PostgreSQL is at revision `0022`. A disposable PostgreSQL database
  completed a fresh full upgrade, `0022 -> 0021` downgrade, and re-upgrade to
  `0022`, then was deleted without touching the live `stock` database.
- The unmocked synthetic daily loop resolves 3/3 SSE/SZSE/BSE coverage,
  matures a 5-session terminal outcome, publishes a three-item shortlist, and
  on the second invocation reuses the original run/TaskRun lineage without
  revising IDs or terminal metrics.
- The normal API on port 8000 and `/zh/ai-research` on port 3000 are healthy.
  Celery connects to Redis and registers 25 tasks. Real TaskRun
  `41e7f041-a700-4e05-ae7d-ec29f96c8888` completed the expected deferred path
  with progress 3/3 because the development database has only 2/3 exact-date
  coverage and no exchange attribution.
- In-app browser acceptance found no console errors. The rendered workflow is
  ordered daily shortlist, published outcomes, research desk, evidence
  coverage, then full-market screening; empty shortlist/outcome states leave
  all later panels usable. Candidate deep links are covered by the persisted
  shortlist component/page tests because the development database has no
  published cohort.
- Every surface retains the research-only/no-automated-trading boundary. AI
  explanation remains downstream of deterministic membership/ranking, and
  outcomes never feed back into later shortlist weights or membership.
