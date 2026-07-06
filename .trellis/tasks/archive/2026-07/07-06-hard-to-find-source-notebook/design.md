# Hard-to-find Source Notebook Design

## Architecture

Add a user-curated source notebook as a small evidence-adjacent domain object. It should sit beside macro observations, generated reports, and stored news, while preserving the current citation boundary.

Primary layers:

- Domain: new `ResearchSourceNote` ORM model in `packages/domain/models.py`.
- Migration: new Alembic revision after `0010_intraday_minute_cache_entries.py`.
- Service: new `packages/services/research_source_notes.py` for validation, create/list, and citation payload construction.
- API: new FastAPI router under `apps/api/routers/research_source_notes.py`.
- Web proxy: new Next route handlers under `apps/web/app/api/research-source-notes`.
- UI: new client component mounted on `apps/web/app/[locale]/evidence/page.tsx`.
- AI context: citable entries may be added as extra evidence to dashboard and/or market assistant citation builders.

## Data Model

`ResearchSourceNote` fields:

- `id`
- `title`
- `source_url`
- `source_name`
- `source_type`
- `symbols_json`
- `tags_json`
- `published_at`
- `as_of`
- `retrieved_at`
- `excerpt`
- `note`
- `ai_follow_up`
- `review_status`
- `is_citable`
- `metadata_json`
- `created_at`
- `updated_at`

Validation rules:

- `title`, `source_name`, `source_type`, and either `source_url` or excerpt text are required.
- `is_citable=true` requires `review_status=reviewed`, non-empty excerpt, and either `source_url` or enough source name/date metadata to identify the source.
- Tags and symbols are normalized into trimmed, de-duplicated arrays.
- Source URLs remain user-provided metadata; the backend does not fetch them.

## Data Flow

Create flow:

1. User pastes source details or uploads a text/CSV/Markdown-like file in the browser.
2. Browser reads file text with `File.text()` and places it into editable fields.
3. UI posts JSON to `/api/research-source-notes`.
4. Next route proxies to FastAPI `/research-source-notes`.
5. Service validates, normalizes arrays, stores the row, and returns the serialized note.

List flow:

1. Evidence page server component fetches `/research-source-notes`.
2. Page passes notes and localized labels to the notebook client component.
3. Component renders recent entries and client-side filters for MVP scanning.

AI citation flow:

1. Service exposes `list_citable_research_source_note_citations`.
2. Only rows with `is_citable=true` and `review_status=reviewed` produce citation payloads.
3. Citation IDs use `research_source_note:<uuid>`.
4. Dashboard/assistant prompts include these only under allowed citations, never as source-readiness gaps.

## Compatibility

- Existing `NewsArticle`, `GeneratedReport`, and `MarketIndicatorObservation` contracts remain unchanged.
- Existing macro seed browser upload flow remains separate.
- SQLite and PostgreSQL must both work; JSON columns follow existing `JSON().with_variant(JSONB, "postgresql")` pattern.
- No raw binary file content is persisted.

## Trade-offs

- MVP stores excerpts and notes rather than a full document corpus. This keeps licensing and storage boundaries clear while still enabling hard-to-find source capture.
- Citable status is explicit rather than automatic. This adds one checkbox/status decision, but prevents draft links and uploaded text from becoming AI evidence too early.
- Client-side file reading avoids a multipart backend upload path for MVP. It is enough for personal note capture and keeps the backend JSON-only.

## Rollback

- UI can be removed from the Evidence Center without touching existing source readiness or macro seed import.
- API router inclusion can be reverted independently.
- Database rollback drops only the new notebook table.
