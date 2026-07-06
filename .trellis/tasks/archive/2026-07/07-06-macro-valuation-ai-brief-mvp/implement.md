# Implementation Plan

## Pre-Development

- [x] Read this task's `prd.md` and `design.md`.
- [x] Run `python ./.trellis/scripts/get_context.py --mode packages`.
- [x] Read applicable backend/frontend specs via `trellis-before-dev`.
- [x] Confirm current dirty worktree and avoid reverting unrelated changes.

## Step 1: Backend Indicator Registry

- [x] Extend `packages/services/market_indicators.py` with P0 macro definitions.
- [x] Keep `get_buffett_indicator_payloads` backward compatible or replace call sites with a broader helper while preserving dashboard payload shape.
- [x] Add/adjust tests:
  - `tests/services/test_market_indicators_service.py`
  - `tests/services/test_market_dashboard_service.py`
  - `tests/api/test_dashboard_api.py`

## Step 2: Daily Brief Service

- [x] Add deterministic daily brief logic using dashboard payload evidence.
- [x] Keep the brief helper in `packages/services/market_dashboard.py` while the logic remains compact.
- [x] Include sections:
  - what changed.
  - why it matters.
  - what to watch next.
  - data gaps.
- [x] Include diagnostics and evidence/source references.
- [x] Test no-data and partial-data cases.

## Step 3: API Payload Integration

- [x] Add brief data to `/dashboard/market-overview` or a small companion route.
- [x] Preserve existing market overview fields.
- [x] Ensure no-data macro indicators do not break frontend rendering.

## Step 4: Frontend Dashboard

- [x] Update `apps/web/app/[locale]/page.tsx` to render macro/valuation groups and the daily brief.
- [x] Update `apps/web/messages/en.json` and `apps/web/messages/zh.json`.
- [x] Update or add tests in `apps/web/app/[locale]/page.test.tsx`.
- [x] Keep mobile and desktop layout stable.

## Step 5: Documentation

- [x] Update `README.md`.
- [x] Update `docs/manual/user-guide.md`.
- [x] Keep professional comparison focused on information aggregation and AI research.
- [x] Avoid overclaiming live macro feeds or investment advice.

## Validation Commands

Focused checks:

```powershell
pytest tests/services/test_market_indicators_service.py tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py
npm run test:web -- --reporter=dot apps/web/app/[locale]/page.test.tsx
```

Full checks before close:

```powershell
pytest
npm run test:web -- --reporter=dot
git diff --check
```

## Validation Results

- [x] `pytest tests/services/test_market_indicators_service.py tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py` - passed.
- [x] `npm run test:web -- --reporter=dot apps/web/app/[locale]/page.test.tsx` - passed.
- [x] `pytest` - passed, 291 tests.
- [x] `npm run test:web -- --reporter=dot` - passed, 120 tests.
- [x] `npx tsc --noEmit -p apps/web/tsconfig.json` - passed after adding the TypeScript 6 deprecation compatibility setting and fixing the market overview item type.
- [x] `ruff check packages/services/market_indicators.py packages/services/market_dashboard.py tests/services/test_market_indicators_service.py tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py` - passed.
- [x] `git diff --check` - passed; Git emitted line-ending conversion warnings only.
- [ ] `ruff check .` - not clean because of pre-existing lint debt outside this task, including `.trellis/scripts/common/__init__.py`, `.trellis/scripts/common/session_context.py`, `apps/api/routers/settings.py`, `packages/services/news.py`, `packages/services/smart_recommendations.py`, `scripts/provider_readiness.py`, and unrelated tests/scripts.
- [ ] `mypy apps packages` - not clean because of pre-existing type debt and missing third-party stubs across providers/services; after local frontend type fixes, the changed frontend typecheck passes through `npx tsc`.

## Risk Points

- Existing dashboard tests may assert exact indicator counts.
- Translation strings may contain existing encoding issues; keep edits minimal and ASCII where possible unless the file already contains Chinese text.
- Existing user changes in dashboard files must be preserved.
- Do not add live source claims unless a real source adapter is implemented and verified.
