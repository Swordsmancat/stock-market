# Hard-to-find Source Notebook Implementation Plan

## Checklist

- [x] Read backend database, API, quality, and assistant citation specs before editing.
- [x] Read frontend component, state, type-safety, and quality specs before editing.
- [x] Add `ResearchSourceNote` ORM model and Alembic migration.
- [x] Add service functions for normalization, validation, create/list, serialization, and citable citation payloads.
- [x] Add FastAPI router and include it in `apps/api/main.py`.
- [x] Add backend tests for model/migration, service validation, API create/list, and citable-only citation payloads.
- [x] Add Next API proxy route and route tests.
- [x] Add Source Notebook client component with paste fields, browser file upload, status controls, and recent-entry display.
- [x] Mount the component on the Evidence Center page and localize all labels in `en.json` and `zh.json`.
- [x] Add/update frontend tests for render, create flow, file upload prefill, and non-citable/citable labels.
- [x] Wire citable notebook entries into the dashboard or assistant AI citation pipeline with unknown-citation validation preserved.
- [x] Run focused backend and frontend tests.
- [x] Run Trellis quality check and finish-work flow before commit.

## Validation Commands

- `pytest tests/domain/test_migrations.py tests/domain/test_models.py`
- `pytest tests/services/test_research_source_notes_service.py tests/api/test_research_source_notes_api.py tests/services/test_market_dashboard_service.py`
- `pnpm --dir apps/web test -- research-source-notes`
- `pnpm --dir apps/web test -- evidence`

## Risk Points

- Citation validation must recognize the new `research_source_note:<uuid>` IDs only when they were included in allowed citations.
- Uploaded browser file contents must remain editable user-provided text, not an automatic evidence ingestion pipeline.
- Date serialization must stay stable between Python API payloads and Next rendering.
- Large excerpts should be clipped for AI prompt payloads and UI previews.

## Review Gate

Before starting implementation, confirm that the PRD/design/implementation plan preserve the user's product direction: personal information aggregation, macro/valuation evidence collection, and AI summaries/recommendations rather than professional trading-site parity.
