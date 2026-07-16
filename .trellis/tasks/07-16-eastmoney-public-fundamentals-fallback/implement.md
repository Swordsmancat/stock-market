# Eastmoney public fundamentals fallback execution plan

## 1. Provider TDD

- Add fixtures for complete financial rows, company survey rows, empty data,
  malformed identity/date/numeric fields, oversized responses, redirects,
  timeouts, and credential-free request assertions.
- Run red, implement the fixed-host HTTP adapter and normalized dataclasses,
  then run provider tests green.

## 2. Service and cache TDD

- Add database-first zero-call, eligible fallback, no-data/unavailable,
  no-write, Redis hit, and Redis failure tests.
- Implement the smallest database-first service branch and normalized cache.
- Preserve existing ingestion functions and non-A-share fixture behavior.

## 3. Detail and AI integration

- Extend TypeScript payload types and render bounded company context inside the
  existing fundamentals section without adding a new module.
- Extend assistant fundamental citation summary/metadata with bounded company
  context and provenance.
- Add component/page and assistant regressions.

## 4. Validate

```powershell
python -m pytest -q tests/providers/test_eastmoney_public_fundamentals_provider.py
python -m pytest -q tests/services/test_fundamentals_service.py tests/api/test_fundamentals_api.py
python -m pytest -q tests/services/test_market_assistant_service.py
python -m ruff check packages/providers/eastmoney_public_fundamentals.py packages/services/fundamentals.py packages/services/market_assistant.py
npm run test:web -- --run apps/web/app/[locale]/instruments/[symbol]/page.test.tsx
npx tsc --noEmit -p apps/web/tsconfig.json
python ./.trellis/scripts/task.py validate 07-16-eastmoney-public-fundamentals-fallback
git diff --check
```

- Run relevant full Python and web groups after focused checks.
- Run one bounded live provider read and API/detail/assistant smoke without
  printing raw bodies or making database writes.

## 5. Finish

- Update the executable backend contract with provider, cache, no-write,
  detail, and citation behavior.
- Commit only task-owned changes, archive the implementation task, record the
  journal, and push. Leave five-day acceptance and worktree metadata untouched.
