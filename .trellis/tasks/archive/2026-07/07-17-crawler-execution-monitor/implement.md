# Crawler execution monitor implementation

1. Read TaskRun, Celery schedule, backend/frontend, and cross-layer specifications; inspect real production TaskRun names and input shapes read-only.
2. Add the curated read-only monitor service with deterministic selectors, classification, sanitization, summary, and focused service tests.
3. Add the FastAPI route and API tests proving empty/failure-free database-only behavior.
4. Add shared frontend payload types/decoder and tests.
5. Build the localized server page, 30-second refresh control, compact status strip, responsive detail view, and explicit failed/empty states.
6. Add desktop navigation, breadcrumb mapping, and Chinese/English messages while preserving the mobile five-item list.
7. Run focused then full Ruff, formatting, pytest, Vitest, and TypeScript checks; run Trellis Check and fix findings.
8. Reload only API/Web containers, verify production status projection, and visually inspect desktop/mobile light/dark layouts and console logs.
9. Capture any durable cross-layer contract in Trellis specs and leave commit/archive work pending unless explicitly requested.

## Rollback Points

- The service/router are additive and do not alter TaskRun state or schemas.
- The route/sidebar entry can be reverted without affecting crawler execution.
