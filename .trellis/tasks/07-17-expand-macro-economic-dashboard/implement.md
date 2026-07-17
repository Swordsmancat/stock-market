# Implementation Plan

1. Add failing provider/service/API tests for first-batch definitions,
   normalization, grouped history, partial failures, and bounded diagnostics.
2. Implement the AkShare macro provider normalizer and extend market-indicator
   definitions, refresh service, history projection, and API routes.
3. Add failing frontend component/page/proxy tests for grouped cards,
   localization, refresh behavior, trends, truthful missing states, and closed
   maintenance detail.
4. Implement the macro dashboard component, local proxy, translations, and
   evidence-page composition.
5. Run focused tests, full backend and Web suites, lint/type checks, JSON and
   diff validation.
6. Browser-smoke Chinese/English desktop and 375px layouts on an isolated Web,
   then build/deploy affected Docker services.
7. Run one explicit live AkShare refresh, verify stored data and 3000/8000
   health, update specs, complete Trellis checks, commit, archive, journal, and
   push.

## Risk and rollback points

- Provider schemas: adapter tests and family-scoped failure prevent broad data
  corruption.
- Page size: existing sections stay intact and are only wrapped after their
  existing tests are updated.
- Runtime provider access: no GET-triggered refresh; the live refresh is a
  separate post-deploy operation.

## Validation commands

```powershell
pytest tests/providers tests/services tests/api -q
npm run test:web
npx tsc --noEmit -p apps/web/tsconfig.json
python ./.trellis/scripts/task.py validate 07-17-expand-macro-economic-dashboard
git diff --check
```
