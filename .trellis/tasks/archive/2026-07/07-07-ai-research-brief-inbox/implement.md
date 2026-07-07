# AI Research Brief Inbox Implementation Plan

## Checklist

1. Load pre-development specs for backend, frontend, and cross-layer changes.
2. Add backend persistence:
   - `ResearchBrief` ORM model.
   - Alembic migration `0012_research_briefs.py`.
   - Migration test coverage.
3. Add research brief service:
   - context assembly from `get_market_overview_payload`;
   - deterministic fallback generator;
   - optional LLM generator;
   - citation validation;
   - create/list serialization.
4. Add FastAPI router and register it in `apps/api/main.py`.
5. Add backend tests for service and API.
6. Add web API proxy and route tests.
7. Add Evidence Center UI:
   - fetch recent briefs server-side;
   - client component for generate action and inbox state;
   - translations in English and Chinese;
   - page/component tests.
8. Update README and manual.
9. Run focused validation:
   - `python -m pytest tests/services/test_research_briefs.py tests/api/test_research_briefs_api.py tests/domain/test_migrations.py -q`
   - `npm run test:web -- apps/web/app/api/research-briefs/route.test.ts apps/web/components/research-brief-inbox.test.tsx apps/web/app/[locale]/evidence/page.test.tsx`
   - `python -m ruff check packages/services/research_briefs.py apps/api/routers/research_briefs.py tests/services/test_research_briefs.py tests/api/test_research_briefs_api.py`
   - `npx tsc -p apps/web/tsconfig.json --noEmit`
10. Run broader validation if focused checks pass:
    - `python -m pytest -q`
    - `npm run test:web`
    - `git diff --check`

## Risk Notes

- `packages/domain/models.py` already has unrelated dirty changes. Read carefully before editing and preserve existing user work.
- Citation validation should not accept source-readiness links, seed templates, drafts, or queue-only IDs as citations.
- Market overview generation may call provider-backed market data. Tests should use mocked or local session fixtures.
- `apps/web/app/[locale]/evidence/page.tsx` is large; keep UI additions localized and prefer a separate client component for generate/inbox interaction.

## Review Gate Before Start

Proceed to `task.py start` only after the planning artifacts exist and current user approval to execute is treated as approval for this implementation slice.
