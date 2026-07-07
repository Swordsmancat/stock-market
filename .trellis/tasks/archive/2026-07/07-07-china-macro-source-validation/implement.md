# Implementation Plan

## Scope Decision

This task is validation-only. Do not implement a production NBS/PBOC/Trading Economics/AkShare/Tushare adapter in this task. The deliverable is a repeatable validation path plus durable capability metadata that identifies the safest next adapter candidate.

## Pre-Implementation

- Keep unrelated dirty files untouched:
  - `apps/web/components/navigation-items.test.ts`
  - `apps/web/components/navigation-items.ts`
  - `packages/services/market_assistant.py`
  - `tests/ai/test_market_assistant.py`
- Before code edits, load `trellis-before-dev` and relevant backend/frontend spec indexes.
- Re-read these specs when implementing:
  - `.trellis/spec/backend/index.md`
  - `.trellis/spec/backend/error-handling.md`
  - `.trellis/spec/backend/quality-guidelines.md`
  - `.trellis/spec/backend/logging-guidelines.md`
  - `.trellis/spec/backend/assistant-research-citation-contract.md`
  - `.trellis/spec/backend/market-indicator-seed-import-contract.md`
  - `.trellis/spec/frontend/index.md` if any Evidence Center or homepage UI changes.

## Ordered Work

1. Add capability registry tests.
   - Assert China macro source candidates include NBS, PBOC, World Bank/global fallback, vendor API, and library wrapper rows.
   - Assert enum/status fields serialize predictably.
   - Assert candidate/manual/probe rows are not marked as citable evidence.

2. Add capability registry implementation.
   - Prefer `packages/services/source_capabilities.py`.
   - Use frozen dataclasses and explicit tuples, matching current `information_sources.py` style.
   - Include stable IDs, collection links, license/freshness notes, and recommended next actions.

3. Add probe script tests.
   - Cover default no-network output.
   - Cover focused source selection.
   - Cover fake live-probe OK/WARN/FAIL behavior without real network.
   - Cover sanitized errors and unknown source handling.

4. Add validation/probe script.
   - Example: `scripts/validate_china_macro_sources.py`.
   - Default behavior: summarize registry and mark live probe as skipped.
   - Optional behavior: `--live-network` runs shallow checks.
   - Do not write market observations or mutate the database.

5. Integrate capability metadata additively.
   - Preferred: add source capability summary to `get_information_source_readiness_payload(...)` diagnostics or a new additive field if it stays small.
   - Preserve existing status/evidence semantics.
   - Add service tests proving readiness IDs/probe IDs do not become citations.

6. Update docs.
   - User guide: explain validated China macro source state and why this is not AI evidence yet.
   - Developer runbook: explain how to rerun the validation script, interpret statuses, and select the next adapter candidate.
   - README: update roadmap/status if the capability matrix becomes user-visible.

7. Optional live research pass.
   - If live network is used, keep results summarized in docs or capability notes.
   - Do not let live probe output be the only source of truth for tests.

## Validation Commands

Focused checks:

```bash
pytest tests/services/test_source_capabilities.py
pytest tests/scripts/test_validate_china_macro_sources.py
pytest tests/services/test_information_sources_service.py
```

If frontend payload or UI changes:

```bash
npm run test:web -- apps/web/app/[locale]/evidence/page.test.tsx
npm run test:web -- apps/web/app/[locale]/page.test.tsx
npx tsc -p apps/web/tsconfig.json --noEmit
```

Final checks before commit:

```bash
pytest -q
npm run test:web
npx tsc -p apps/web/tsconfig.json --noEmit
node -e "JSON.parse(require('fs').readFileSync('apps/web/messages/en.json','utf8')); JSON.parse(require('fs').readFileSync('apps/web/messages/zh.json','utf8'))"
ruff check packages/services/source_capabilities.py scripts/validate_china_macro_sources.py tests/services/test_source_capabilities.py tests/scripts/test_validate_china_macro_sources.py
git diff --check
```

## Review Gate Before Start

- User approves the validation-only PRD/design/implement artifacts.
- Run:

```bash
python ./.trellis/scripts/task.py start .trellis/tasks/07-07-china-macro-source-validation
```

Then continue to Phase 2 implementation in inline mode.

## Rollback Points

- Registry-only changes can be reverted without touching scripts or docs.
- Probe script can be reverted independently if live behavior proves too flaky.
- Source-readiness payload integration can be removed while keeping the registry and docs.
