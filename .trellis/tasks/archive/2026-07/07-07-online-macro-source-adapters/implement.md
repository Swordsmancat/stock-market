# Implementation Plan

## Pre-Implementation

- Keep unrelated dirty files untouched:
  - `apps/web/components/navigation-items.test.ts`
  - `apps/web/components/navigation-items.ts`
  - `packages/services/market_assistant.py`
  - `tests/ai/test_market_assistant.py`
- Before code edits, load Trellis backend/frontend specs through `trellis-before-dev`.
- Re-read:
  - `.trellis/spec/backend/index.md`
  - `.trellis/spec/backend/error-handling.md`
  - `.trellis/spec/backend/quality-guidelines.md`
  - `.trellis/spec/backend/market-indicator-seed-import-contract.md`
  - `.trellis/spec/backend/assistant-research-citation-contract.md`
  - `.trellis/spec/frontend/index.md` if Evidence Center UI text or behavior changes.

## Ordered Work

1. Add World Bank provider tests.
   - Successful latest observation.
   - Missing/null observation skipped.
   - Unexpected schema failure.
   - Timeout/network failure sanitized.
   - No tests should hit live World Bank.

2. Add provider implementation.
   - New `packages/providers/world_bank_provider.py`.
   - Typed observation/result dataclasses.
   - Configurable base URL with official default.
   - Normalized missing-value handling.

3. Add macro refresh service tests.
   - Maps `USA`, `CHN`, and `HKG` World Bank observations to existing Buffett codes.
   - Writes through `MarketIndicatorObservationSeed` and existing upsert helper.
   - Dry-run does not write.
   - Skipped targets produce diagnostics.
   - Stored components contain source and methodology metadata.

4. Add service implementation.
   - Prefer a small function near the FRED refresh path unless implementation pressure proves a separate service module is cleaner.
   - Keep transactions all-or-nothing for validated writes where practical.
   - Preserve existing market indicator definitions.

5. Add refresh script and script tests.
   - Example name: `scripts/refresh_world_bank_macro_indicators.py`.
   - Support dry-run and latest-only/default latest behavior.
   - Print concise OK/WARN/FAIL status.

6. Update source readiness.
   - Add or update World Bank Buffett source readiness item.
   - Keep manual Buffett seed guidance as fallback.
   - Add service tests for configured/no-data/manual fallback states.

7. Update frontend only if payload labels or Evidence Center source-readiness display needs additive copy.
   - Keep UI dense and research-workflow oriented.
   - Update i18n JSON and page tests if visible text changes.

8. Update docs.
   - README and user manual for World Bank refresh usage and citation boundary.
   - Maintainer/runbook docs if a new command or env variable is added.

## Validation Commands

Run focused checks first:

```bash
pytest tests/providers/test_world_bank_provider.py
pytest tests/services/test_market_indicators_world_bank_refresh.py
pytest tests/scripts/test_refresh_world_bank_macro_indicators.py
pytest tests/services/test_information_sources_service.py
```

If frontend/source-readiness UI changes:

```bash
npm run test:web -- apps/web/app/[locale]/evidence/page.test.tsx
npx tsc -p apps/web/tsconfig.json --noEmit
```

Final checks before commit:

```bash
pytest
npm run test:web
npx tsc -p apps/web/tsconfig.json --noEmit
node -e "JSON.parse(require('fs').readFileSync('apps/web/messages/en.json','utf8')); JSON.parse(require('fs').readFileSync('apps/web/messages/zh.json','utf8'))"
git diff --check
```

## Rollback Points

- Provider-only changes can be reverted without touching persistence.
- Service refresh changes should be reverted together with script tests if mapping assumptions are wrong.
- Source-readiness UI/docs are additive and can be rolled back separately from stored observation support.

## Review Gate Before `task.py start`

- User approves the open MVP decision in `prd.md`.
- Planning artifacts have been reviewed.
- Task is started with:

```bash
python ./.trellis/scripts/task.py start .trellis/tasks/07-07-online-macro-source-adapters
```
