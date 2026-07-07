# Implementation Plan

## Scope Decision

This is an inline Codex task. Do not dispatch implement/check subagents.

The first implementation slice should verify and productize the official macro refresh paths that already exist. Avoid duplicating provider/service code unless tests reveal a concrete defect.

## Pre-Implementation

- Use `trellis-before-dev` before editing runtime code.
- Read relevant specs:
  - `.trellis/spec/backend/index.md`
  - `.trellis/spec/backend/market-indicator-seed-import-contract.md`
  - `.trellis/spec/backend/assistant-research-citation-contract.md`
  - `.trellis/spec/backend/quality-guidelines.md`
  - `.trellis/spec/frontend/index.md` if any UI/docs route changes touch web code.
- Treat existing dirty paths carefully:
  - `apps/web/components/navigation-items.ts`
  - `apps/web/components/navigation-items.test.ts`
  - `packages/services/market_assistant.py`
  - `tests/ai/test_market_assistant.py`
  These currently show as modified in git status but have no content diff from this session.

## Discovery Checklist

1. Inspect current provider/service/script tests:
   - `tests/providers/test_fred_provider.py`
   - `tests/providers/test_world_bank_provider.py`
   - `tests/services/test_market_indicators_service.py`
   - script tests for `refresh_fred_macro_indicators.py` and `refresh_world_bank_macro_indicators.py`
2. Inspect dashboard/API tests that assert source guidance does not become citations:
   - `tests/api/test_dashboard_api.py`
   - `tests/services/test_market_dashboard_service.py`
3. Inspect docs/manual locations and decide where the runbook belongs.

## Ordered Work

### 1. Verify Existing Official Refresh Behavior

- Run focused tests for FRED provider/service/script behavior.
- Run focused tests for World Bank provider/service/script behavior.
- If tests fail, fix only the concrete defect.
- If tests pass, record current capabilities in the task notes or implementation summary.

### 2. Add Or Improve Operator Runbook

- Add a concise manual page or section documenting:
  - environment variables;
  - FRED command examples;
  - World Bank command examples;
  - dry-run commands;
  - how to verify homepage/Macro Research values;
  - known gaps such as `cn_m2_yoy`.
- Keep language clear that refresh writes local audited observations and that source links/templates are not citations.

### 3. Optional UI Guidance

- If inspection shows a natural existing place, add a small guidance block in Settings or Macro Research.
- Do not add web-triggered refresh mutation unless the user explicitly chooses that scope.
- If UI changes are made, localize strings in both `apps/web/messages/en.json` and `apps/web/messages/zh.json`.

### 4. Data Closure Check

- Using tests or a local dry-run/fake-provider path, prove refreshed official observations flow into:
  - `get_macro_indicator_payloads(...)`;
  - `GET /dashboard/market-overview`;
  - homepage macro favorites.
- Ensure missing values still render as gaps.

### 5. Citation Boundary Check

- Assert dashboard brief / assistant / saved-brief citation lists do not include:
  - `fred_us_rates`
  - `seed_template:fred_us_rates`
  - `buffett_manual_valuation_components`
  - source capability IDs
  - probe URLs
- Preserve existing assistant safety boundaries.

## Validation Commands

Focused backend:

```powershell
pytest tests/providers/test_fred_provider.py tests/providers/test_world_bank_provider.py -q
pytest tests/services/test_market_indicators_service.py -q
pytest tests/scripts/test_refresh_fred_macro_indicators.py tests/scripts/test_refresh_world_bank_macro_indicators.py -q
```

Dashboard/citation boundary:

```powershell
pytest tests/api/test_dashboard_api.py tests/services/test_market_dashboard_service.py -q
```

If web code changes:

```powershell
npx tsc -p apps/web/tsconfig.json --noEmit
npm run test:web -- --reporter=dot
```

Final checks:

```powershell
git diff --check
python ./.trellis/scripts/task.py validate .trellis/tasks/07-07-official-macro-indicator-refresh
```

## Review Gate Before Start

- User reviews and approves `prd.md`, `design.md`, and `implement.md`.
- Decide the open product question:
  - recommended: runbook/status guidance only in this task;
  - later: web-triggered refresh buttons.
- Then run:

```powershell
python ./.trellis/scripts/task.py start .trellis/tasks/07-07-official-macro-indicator-refresh
```

## Rollback Points

- Documentation-only additions can be reverted independently.
- UI guidance can be reverted without touching provider/service refresh logic.
- Service fixes should remain small and covered by focused tests.
