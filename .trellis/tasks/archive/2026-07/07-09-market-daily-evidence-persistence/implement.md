# Market Daily Evidence Persistence MVP Implementation Plan

## Planning Gate

- [x] User approved creating a Trellis task.
- [x] User confirmed `hot_sector` is included in MVP scope.
- [x] Resolve OD2: immediate citable provider-verified rows vs manual review
  gate.
- [x] Run `python ./.trellis/scripts/task.py validate .trellis/tasks/07-09-market-daily-evidence-persistence`.
- [x] Run `python ./.trellis/scripts/get_context.py --mode phase --step 1.4 --platform codex`.
- [x] Start the task only after the user reviews/approves planning artifacts.

## Pre-Development Context

- [x] Load `trellis-before-dev` before editing runtime code.
- [x] Read backend specs:
  - `.trellis/spec/backend/index.md`
  - `.trellis/spec/backend/market-daily-data-contract.md`
  - `.trellis/spec/backend/assistant-research-citation-contract.md`
  - `.trellis/spec/backend/hot-sector-contract.md`
  - `.trellis/spec/backend/database-guidelines.md`
  - `.trellis/spec/backend/error-handling.md`
  - `.trellis/spec/backend/quality-guidelines.md`
- [x] Read frontend specs if touching visible UI:
  - `.trellis/spec/frontend/index.md`
  - `.trellis/spec/frontend/component-guidelines.md`
  - `.trellis/spec/frontend/quality-guidelines.md`
  - `.trellis/spec/frontend/type-safety.md`
- [x] Read shared guides:
  - `.trellis/spec/guides/index.md`
  - `.trellis/spec/guides/cross-layer-thinking-guide.md`
  - `.trellis/spec/guides/code-reuse-thinking-guide.md`

## Backend Storage

- [x] Add `MarketDailyEvidenceEvent` SQLAlchemy model.
- [x] Add Alembic migration `0013_market_daily_evidence_events.py`.
- [x] Extend migration tests for table and key columns.
- [x] Add model/schema tests as needed.

## Import and Citation Service

- [x] Add `packages/services/market_daily_evidence.py`.
- [x] Normalize event identities for all MVP event types:
  - `stock_fund_flow`
  - `limit_up_reason`
  - `dragon_tiger_list`
  - `block_trade`
  - `hot_sector`
- [x] Implement deterministic citation ID builder:
  `market_daily_event:<event_type>:<identity>:<trade_date>`.
- [x] Implement import/upsert from normalized provider payloads.
- [x] Implement listing and citation helpers for stored rows.
- [x] Add sanitized diagnostics for unavailable payloads, empty rows, and
  storage failures.

## API

- [x] Add FastAPI router endpoints for manual import and list/read.
- [x] Wire router in `apps/api/main.py`.
- [x] Add API tests for query/body normalization, import counts, unsupported
  event types, empty payloads, and stored citation payloads.
- [x] Add Next.js route proxies for list/read and refresh/import actions.

## Citation Integration

- [x] Add `market_daily_event:` to assistant/dashboard/research brief allowed
  prefixes only where stored evidence is assembled.
- [x] Add stored market daily evidence citations to market assistant context.
- [x] Add stored market daily evidence citations to dashboard/research brief
  context if suitable for current surfaces.
- [x] Test that live provider payloads still do not become citations.
- [x] Test that unknown `market_daily_event:*` IDs are rejected by citation
  validation.

## UI / Frontend

- [x] Add a minimal existing-page frontend entry for stored market daily
  evidence availability and citations.
- [x] Add a "refresh today's market evidence" action that calls the import
  proxy and refreshes the summary.
- [x] Update
  `apps/web/messages/en.json` and `apps/web/messages/zh.json` together.
- [x] Add/extend frontend tests for visible counts, latest import metadata,
  citation IDs, refresh counts, and diagnostics.
- [x] Keep UI copy research-only and avoid trading instructions.

## Documentation and Spec

- [x] Update `.trellis/spec/backend/market-daily-data-contract.md`.
- [x] Update `.trellis/spec/backend/assistant-research-citation-contract.md`.
- [x] Update `docs/runbooks/instock-analysis-integration.md`.

## Validation

Focused backend:

```powershell
pytest tests/domain/test_migrations.py tests/services/test_market_daily_evidence.py tests/api/test_market_daily_evidence_api.py
python -m ruff check packages/domain/models.py packages/services/market_daily_evidence.py apps/api/routers/market_daily_evidence.py tests/domain/test_migrations.py tests/services/test_market_daily_evidence.py tests/api/test_market_daily_evidence_api.py
```

Assistant/dashboard integration checks, exact files to refine after coding:

```powershell
pytest tests/ai/test_market_assistant.py tests/services/test_market_dashboard_service.py tests/services/test_research_briefs.py
```

Frontend checks if touched:

```powershell
npm run test:web -- <focused frontend tests>
npx tsc -p apps/web/tsconfig.json --noEmit --ignoreDeprecations 6.0
node -e "JSON.parse(require('fs').readFileSync('apps/web/messages/en.json','utf8')); JSON.parse(require('fs').readFileSync('apps/web/messages/zh.json','utf8')); console.log('messages ok')"
```

Final checks:

```powershell
python .\.trellis\scripts\task.py validate .trellis\tasks\07-09-market-daily-evidence-persistence
pytest -q
npm run test:web
git diff --check
```

## Rollback Points

- If schema scope grows too large, keep only storage + import + listing and defer
  assistant/dashboard citation integration.
- If citation integration risks weakening validation, keep the new prefix out of
  allowed lists until stored-citation assembly is fully tested.
- If UI scope becomes too large, keep MVP backend/API-only and plan a separate
  Evidence Center explorer.

## Validation Results (2026-07-10)

- [x] Focused migration/service/API and citation integration tests passed.
- [x] Full backend suite passed: `488 passed`.
- [x] Full web suite passed: `58` files / `185` tests.
- [x] `ruff` passed for all touched Python files.
- [x] TypeScript passed with `--noEmit`.
- [x] English/Chinese message JSON parsing passed.
- [x] Trellis task validation passed.
- [x] `git diff --check` passed; only repository line-ending warnings remain.
