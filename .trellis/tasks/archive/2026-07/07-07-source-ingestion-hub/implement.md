# Source Ingestion Hub Implementation Plan

## Scope

Implement the Source Ingestion Hub MVP:

- Browser-readable text-like upload and pasted text stay in the Evidence Center / Source Notebook flow.
- LLM-assisted extraction produces summary, key indicators, citation clues, metadata suggestions, and follow-up questions.
- Deterministic fallback keeps the workflow usable and testable without LLM configuration.
- Saving remains explicit through existing Source Notebook draft/review/citable controls.

## Preconditions

- [x] `prd.md` exists and has passed convergence for the MVP scope.
- [x] `design.md` exists for the complex task.
- [x] User reviews and approves planning before `task.py start`.
- [x] After task start and before code edits, load `trellis-before-dev` for backend/frontend specs.

## Implementation Checklist

1. Backend extraction service
   - [x] Add `packages/services/source_ingestion.py`.
   - [x] Define extraction input/result dataclasses or typed helpers.
   - [x] Add bounded content clipping and basic validation.
   - [x] Implement deterministic fallback extraction for summary, key indicators, citation clues, suggested fields, and follow-up questions.
   - [x] Implement optional OpenAI-compatible LLM extraction via `get_platform_settings()` and `get_llm_provider()`.
   - [x] Strictly parse/normalize LLM JSON and fall back on empty/invalid/failed output.
   - [x] Ensure diagnostics never expose API keys, raw provider payloads, stack traces, or prompt internals.

2. Backend API
   - [x] Add `apps/api/routers/source_ingestion.py` with `POST /source-ingestion/extract`.
   - [x] Register the router in `apps/api/main.py`.
   - [x] Keep response payload JSON-only and backward independent from the Source Notebook create/list API.

3. Web proxy
   - [x] Add `apps/web/app/api/source-ingestion/extract/route.ts`.
   - [x] Add proxy tests covering success and backend validation/error preservation.

4. Evidence Center UI
   - [x] Extend `apps/web/components/research-source-notebook.tsx` with Source Ingestion Hub / AI extraction controls.
   - [x] Reuse existing file upload, source target, and form state.
   - [x] Add extraction button/loading/error states.
   - [x] Render extraction status, model/fallback badge, summary, key indicators, citation clues, and follow-up questions.
   - [x] Add an apply-suggestions action that fills editable form fields without auto-saving or auto-marking citable.
   - [x] Preserve existing save, filter, list, completeness checklist, and citable-boundary behavior.

5. Localization and page wiring
   - [x] Add English and Chinese labels in `apps/web/messages/en.json` and `apps/web/messages/zh.json`.
   - [x] Pass new labels from `apps/web/app/[locale]/evidence/page.tsx` into `ResearchSourceNotebook`.

6. Documentation
   - [x] Update `README.md` current capability table/Source Notebook section.
   - [x] Update `docs/manual/user-guide.md` with the ingestion hub, LLM/fallback extraction, accepted file formats, and citation boundary.

7. Tests
   - [x] Add `tests/services/test_source_ingestion.py`.
   - [x] Add `tests/api/test_source_ingestion_api.py`.
   - [x] Add `apps/web/app/api/source-ingestion/extract/route.test.ts`.
   - [x] Extend `apps/web/components/research-source-notebook.test.tsx` for extraction request, fallback/result rendering, apply-suggestions, and no auto-citable behavior.
   - [x] Extend Evidence Center/page tests only if page wiring requires payload/label assertions.

## Validation Commands

Run focused checks first:

```powershell
python -m pytest tests/services/test_source_ingestion.py tests/api/test_source_ingestion_api.py tests/services/test_research_source_notes_service.py tests/api/test_research_source_notes_api.py -q
npm run test:web -- apps/web/app/api/source-ingestion/extract/route.test.ts apps/web/components/research-source-notebook.test.tsx apps/web/app/[locale]/evidence/page.test.tsx
python -m ruff check packages/services/source_ingestion.py apps/api/routers/source_ingestion.py tests/services/test_source_ingestion.py tests/api/test_source_ingestion_api.py
npx tsc -p apps/web/tsconfig.json --noEmit
git diff --check
```

Results:

- `python -m pytest tests/services/test_source_ingestion.py tests/api/test_source_ingestion_api.py tests/services/test_research_source_notes_service.py tests/api/test_research_source_notes_api.py -q` -> 15 passed.
- `npm run test:web -- apps/web/app/api/source-ingestion/extract/route.test.ts apps/web/components/research-source-notebook.test.tsx apps/web/app/[locale]/evidence/page.test.tsx` -> 3 files passed, 9 tests passed.
- `python -m ruff check packages/services/source_ingestion.py apps/api/routers/source_ingestion.py tests/services/test_source_ingestion.py tests/api/test_source_ingestion_api.py` -> passed.
- `npx tsc -p apps/web/tsconfig.json --noEmit` -> passed.
- `git diff --check` -> passed; CRLF conversion warnings only.

If focused checks pass and touched surface is broad, run broader suites:

```powershell
python -m pytest -q
npm run test:web
```

Results:

- `python -m pytest -q` -> 348 passed.
- `npm run test:web` -> 44 files passed, 143 tests passed.

## Risky Files And Rollback Points

- `apps/web/components/research-source-notebook.tsx`: highest UI risk because it owns current Source Notebook create/list behavior. Keep changes additive and test existing save/filter behavior.
- `apps/web/messages/en.json` and `apps/web/messages/zh.json`: keep key additions aligned across locales.
- `apps/api/main.py`: router registration is simple but affects API startup.
- `packages/services/source_ingestion.py`: keep LLM fallback deterministic and avoid importing web/UI concerns.

Rollback:

- Remove `source_ingestion` service/router/proxy and extraction UI additions.
- Existing Source Notebook data remains valid because no schema change is planned.

## Worktree Notes

There are pre-existing unrelated dirty files outside this task's planned scope:

- `apps/web/components/navigation-items.test.ts`
- `apps/web/components/navigation-items.ts`
- `packages/domain/models.py`
- `packages/services/market_assistant.py`
- `tests/ai/test_market_assistant.py`

Do not revert or include those changes unless the user explicitly asks.
