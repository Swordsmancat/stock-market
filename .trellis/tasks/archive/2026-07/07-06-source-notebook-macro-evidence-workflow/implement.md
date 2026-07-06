# Source Notebook Macro Evidence Workflow Implementation Plan

## Checklist

- [x] Read backend specs: database, API/error handling, assistant citation contract, quality guidelines.
- [x] Read frontend specs: component guidelines, state management, type safety, quality guidelines.
- [x] Add workflow metadata normalization and completeness helpers in `packages/services/research_source_notes.py`.
- [x] Extend `ResearchSourceNoteInput` and API request model additively for source linkage fields while preserving raw `metadata`.
- [x] Include workflow metadata in serialized notes and citable source-note citation metadata.
- [x] Extend Evidence Center page types to pass source-readiness targets into `ResearchSourceNotebook`.
- [x] Extend `ResearchSourceNotebook` UI with source target selector, component role, target indicator chips/fields, methodology/license inputs, completeness checklist, and linked-note badges.
- [x] Keep browser file upload as client-side `File.text()` excerpt prefill.
- [x] Add/update English and Chinese localization keys.
- [x] Add service/API tests for workflow metadata storage, normalization, completeness state, unsafe URL preservation rules, and backwards compatibility.
- [x] Add dashboard/assistant tests proving linked draft or non-citable notes do not become citations, while linked citable notes carry metadata.
- [x] Add frontend tests for source target selection, checklist display, saved linked note rendering, file upload preservation, and localized text.
- [x] Run focused backend/frontend tests, ruff, TypeScript, and `git diff --check`.
- [x] Update specs/docs if implementation establishes a reusable contract.
- [x] Commit and push after Trellis check passes.

## Validation Commands

```bash
pytest tests/services/test_research_source_notes_service.py tests/api/test_research_source_notes_api.py tests/services/test_market_dashboard_service.py tests/ai/test_market_assistant.py
npm run test:web -- apps/web/app/[locale]/evidence/page.test.tsx apps/web/components/research-source-notebook.test.tsx apps/web/app/api/research-source-notes/route.test.ts
ruff check apps/api/routers/research_source_notes.py packages/services/research_source_notes.py packages/services/market_assistant.py packages/services/market_dashboard.py tests/services/test_research_source_notes_service.py tests/api/test_research_source_notes_api.py tests/services/test_market_dashboard_service.py tests/ai/test_market_assistant.py
npx tsc --noEmit --project apps/web/tsconfig.json
git diff --check
```

If homepage source-mix display changes, also run:

```bash
npm run test:web -- apps/web/app/[locale]/page.test.tsx
```

## Risk Points

- Do not let source-readiness links or seed templates become citations.
- Do not store browser-uploaded raw files; keep only user-reviewed excerpt/note text.
- Do not require a new migration unless metadata-json proves insufficient.
- Preserve old API clients that send only existing fields.
- Avoid JSON-column filtering that behaves differently across SQLite and PostgreSQL.
- Keep AI recommendation boundaries: no direct buy/sell/hold, no target prices, no position sizing.

## Review Gate

Before implementation starts, confirm the MVP scope:

- Implement source-to-indicator linkage and review completeness.
- Leave AI follow-up queue execution for a later Trellis task.
- No automatic seed import, scraping, or raw document corpus.
