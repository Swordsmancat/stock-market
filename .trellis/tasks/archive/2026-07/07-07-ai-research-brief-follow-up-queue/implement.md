# AI Research Brief and Follow-up Queue Implementation Plan

## Preconditions

- Task status remains `planning` until the user approves implementation.
- Before code edits, run `python ./.trellis/scripts/task.py start 07-07-ai-research-brief-follow-up-queue` or the equivalent current-task start command.
- After start and before code edits, load `trellis-before-dev` for backend/frontend implementation guidance.
- Do not dispatch `trellis-implement` or `trellis-check` sub-agents in Codex inline mode.

## Ordered Checklist

1. Backend queue service
   - [x] Complete.
   - Add a pure queue derivation helper under `packages/services/`.
   - Define item kinds, citation policy, priority ordering, summary counts, and safety payload.
   - Cover Source Notebook `ai_follow_up`, completeness gaps, seed-prep actions, and source-readiness gaps.

2. Dashboard payload integration
   - [x] Complete.
   - Extend `get_market_overview_payload(...)` additively with `research_follow_up_queue`.
   - Reuse existing session and readiness payloads.
   - Preserve market overview cache invalidation behavior after Source Notebook saves.

3. Backend tests
   - [x] Complete.
   - Add focused service tests for queue derivation.
   - Extend dashboard service/API tests to assert the additive field and citation-boundary behavior.
   - Assert draft/non-citable notes and source-readiness IDs never expose citation IDs.

4. Frontend types and rendering
   - [x] Complete.
   - Add local TypeScript types for `research_follow_up_queue`.
   - Add a queue panel/component near the Source Notebook on `/evidence`.
   - Render metadata chips, category summaries, citation policy, and safety copy.

5. Localization
   - [x] Complete.
   - Add English strings under `EvidenceCenter`.
   - Add matching Chinese strings under `EvidenceCenter`.
   - Keep Source Notebook labels only for notebook-specific copy.

6. Frontend tests
   - [x] Complete.
   - Extend Evidence Center page tests with queue items from AI follow-up, source gap, seed prep, and citable/non-citable note cases.
   - Assert localized no-trading-advice wording and citation policy rendering.

7. Documentation
   - [x] Complete.
   - Update README/manual only if implementation changes user-visible behavior enough to require manual coverage in this task.
   - Keep docs clear that the queue is deterministic and does not execute LLM briefs.

## Validation Results

- `python -m pytest tests/services/test_research_follow_up_queue.py tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py -q` passed.
- `npm run test:web -- apps/web/app/[locale]/evidence/page.test.tsx apps/web/components/research-source-notebook.test.tsx` passed.
- `python -m pytest -q` passed.
- `npm run test:web` passed.
- `python -m ruff check packages/services/research_follow_up_queue.py packages/services/market_dashboard.py tests/services/test_research_follow_up_queue.py tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py` passed.
- `npx tsc -p apps/web/tsconfig.json --noEmit` passed.
- `git diff --check` passed with Windows LF-to-CRLF warnings only.

## Validation Commands

- `python -m pytest tests/services/test_research_source_notes_service.py tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py -q`
- `npm run test:web -- apps/web/app/[locale]/evidence/page.test.tsx apps/web/components/research-source-notebook.test.tsx`
- `npm run typecheck --workspace apps/web` if the repo supports the workspace command.
- `python -m ruff check packages/services/market_dashboard.py packages/services/research_follow_up_queue.py tests/services/test_market_dashboard_service.py tests/api/test_dashboard_api.py`
- `git diff --check`

Adjust commands to the repository's actual package scripts after reading `package.json` and existing test scripts.

## Risk Points

- Avoid turning source-readiness IDs, seed templates, collection links, or draft notes into citations.
- Avoid adding LLM execution to this MVP.
- Avoid duplicating large note excerpts into the dashboard payload; use clipped prompts/previews where needed.
- Avoid broad UI refactors in Evidence Center; add the queue panel in the existing page structure.
- Preserve existing user changes in currently dirty files.

## Review Gate

Before `task.py start`, confirm with the user that this planning scope is acceptable:

- deterministic queue only;
- no selected-item AI brief generation button in this slice;
- no new persistent queue table;
- no scraping/OCR/vector/document corpus ingestion;
- no trading advice workflow.
