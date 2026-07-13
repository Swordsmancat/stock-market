# Persisted daily research shortlist - implementation plan

## 1. Backend contract and persistence

- Add focused scorer tests first for every normalization family, dimension
  renormalization, different candidate totals, stable ties, and unknown rules.
- Add run/candidate ORM models and Alembic revision `0020` with upgrade,
  downgrade, indexes, foreign keys, and unique constraints.
- Add model/migration tests following current SQLite-compatible Alembic tests.

## 2. Generation and reads

- Add the internal unbounded eligibility result without changing public limits.
- Implement readiness/decision-date checks, score decomposition, structured
  factors/gaps/invalidation, frozen entry provenance, canonical key, and atomic
  save/read serialization.
- Reuse extracted fail-closed explanation logic; check idempotency before any
  LLM call.
- Test no provider calls, coverage conflicts, stale exclusion, rollback,
  duplicate/concurrent key behavior, deterministic fallback, and immutable
  latest/detail results.

## 3. API

- Add request schema and generate/latest/detail routes; register the router.
- Map value errors to 400, readiness conflicts to 409, and missing UUID resources
  to 404 without leaking internals.
- Add focused API tests for payload passthrough, safety, idempotency, no-data,
  conflict, and detail lookup.

## 4. Frontend

- Add shared shortlist types and latest/generate proxies with route tests.
- Build and test the localized daily shortlist panel: loaded, empty, generating,
  conflict/error, gaps, safety, deep link, and in-page handoff states.
- Server-load latest as optional data, reorder `/ai-research`, and update page
  tests to prove independent degradation.
- Add `DailyResearchShortlist` messages to both locale files and verify JSON.

## 5. Verification

Run focused checks during implementation, then the complete affected-layer gate:

```powershell
python -m pytest tests/services/test_research_shortlists.py tests/api/test_research_shortlists_api.py tests/services/test_stock_selection.py tests/services/test_stock_discovery.py tests/api/test_stock_selection_api.py -q
python -m pytest -q
python -m ruff check packages/services/research_shortlists.py packages/services/stock_selection.py packages/services/stock_discovery.py packages/domain/models.py apps/api/routers/research_shortlists.py tests/services/test_research_shortlists.py tests/api/test_research_shortlists_api.py
npx tsc --noEmit
npm run test:web
python -m json.tool apps/web/messages/en.json > $null
python -m json.tool apps/web/messages/zh.json > $null
python ./.trellis/scripts/task.py validate 07-13-daily-research-shortlist-snapshot
git diff --check
```

Adjust focused filenames only if nearby test organization requires it. Do not
skip the full backend/frontend passes.

## Rollback points

- If scoring review fails, stop before persisting any run and keep old discovery
  unchanged.
- If persistence/API fails, downgrade `0020`; no existing tables are modified.
- If frontend fails, remove the new panel/proxies and restore the previous page
  ordering while retaining tested backend resources.

## Completion Evidence

- Backend: `python -m pytest -q` -> 688 passed.
- Frontend: `npm run test:web` -> 75 files / 220 tests passed.
- TypeScript: `npx tsc --noEmit -p apps/web/tsconfig.json` -> passed.
- Ruff: every changed Python/Alembic file -> passed.
- Locale JSON: English and Chinese catalogs parsed successfully.
- Migration: `alembic heads` -> `0020_research_shortlists (head)`; focused
  migration upgrade/downgrade tests passed.
- Trellis: task context validation passed.
- Whitespace: `git diff --check` passed with line-ending notices only.
- Runtime baseline: normal `3000/zh/ai-research` and `8000/health` remained 200.
- Independent backend and UI re-reviews reported no blocking findings.
