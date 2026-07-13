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
