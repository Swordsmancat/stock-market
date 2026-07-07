# AI Research Brief Inbox Design

## Architecture

This is a vertical slice across the existing Evidence Center stack:

- Domain model: add `ResearchBrief` in `packages/domain/models.py`.
- Migration: add Alembic revision `0012_research_briefs.py`.
- Service: add `packages/services/research_briefs.py`.
- API router: add `apps/api/routers/research_briefs.py` and register it in `apps/api/main.py`.
- Web proxy: add `apps/web/app/api/research-briefs/route.ts`.
- Frontend: integrate a compact inbox/generator into `apps/web/app/[locale]/evidence/page.tsx`, with payload types in `apps/web/lib/market-overview-payload.ts` only if needed by shared types.
- Localization: add messages to `apps/web/messages/en.json` and `apps/web/messages/zh.json`.
- Docs: update `README.md` and `docs/manual/user-guide.md`.

## Data Model

`ResearchBrief` should be separate from `GeneratedReport` because saved briefs are macro/source/evidence synthesis records, not symbol-specific stock reports.

Suggested columns:

- `id`: UUID primary key.
- `title`: short display title.
- `brief_type`: string, default `evidence_center`.
- `scope_json`: JSON metadata describing provider, source context, and optional locale.
- `content_markdown`: generated markdown body.
- `citations_json`: JSON list of allowed citations actually used or available.
- `source_summary_json`: JSON source mix, queue summary, and source gap counts.
- `diagnostics_json`: JSON diagnostics from assembly and generation.
- `model_json`: JSON model metadata with provider, name, used_llm, fallback_reason.
- `safety_json`: JSON safety flags.
- `created_at`: timezone-aware datetime.

## Context Assembly

The service should reuse existing backend functions rather than duplicating source logic:

- `get_market_overview_payload(...)` for dashboard brief, information sources, research follow-up queue, and citations.
- Existing dashboard brief citations are the allowed citation set.
- Research follow-up queue items provide research questions and gaps; they are not citations unless they include an allowed `citation_id`.

This keeps the feature aligned with existing citation gates and source-readiness rules.

## Generation Flow

1. Assemble Evidence Center context with `get_market_overview_payload`.
2. Build allowed citation ID set from `dashboard_brief.citations`.
3. Build deterministic fallback markdown from dashboard sections, citable evidence, source gaps, follow-up questions, diagnostics, and safety note.
4. If OpenAI-compatible settings are configured, call the LLM with a prompt that:
   - allows only provided citation IDs,
   - bans fabricated data and trading advice,
   - asks for concise markdown sections,
   - treats source gaps and queue items as prompts/gaps unless citable.
5. Validate generated markdown for bracketed citation IDs with the same prefix strategy used by dashboard brief narrative.
6. Store LLM output when valid; otherwise store deterministic fallback with diagnostic metadata.

## API Contract

`GET /research-briefs?limit=20`

Returns:

```json
{
  "items": [],
  "summary": {"total": 0, "returned": 0}
}
```

`POST /research-briefs/generate`

Body:

```json
{
  "provider": "mock",
  "locale": "zh",
  "title": "optional title"
}
```

Returns the serialized saved brief plus `status: "stored"`.

## Frontend Shape

The Evidence Center should show:

- Generate button with pending state.
- Recent saved briefs with title, created date, model badge, safety/citation counts, and markdown preview.
- Empty state when no saved briefs exist.
- Degraded/error copy when list or generate requests fail.

Keep it compact and work-focused. The page already contains dense evidence sections, so the inbox should fit that operational style.

## Compatibility And Rollback

- Existing endpoints and payloads remain additive.
- Existing `GeneratedReport` behavior is untouched.
- Existing Source Notebook citation rules are reused, not loosened.
- Rollback is dropping the new route/UI integration and table migration.
