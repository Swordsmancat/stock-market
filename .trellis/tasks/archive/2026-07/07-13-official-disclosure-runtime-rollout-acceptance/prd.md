# Official disclosure runtime rollout acceptance

## Goal

Move the completed official-disclosure metadata, document, operations, and incremental-monitoring code from repository state into the normal local PostgreSQL/API/Celery runtime, then prove the watchlist monitor works against a controlled live CNINFO canary without disrupting the existing frontend or losing database state.

## Background

- Repository and `origin/master` are synchronized at `5a392c2` with Alembic head `0019_official_disclosure_monitoring`.
- The normal PostgreSQL database is healthy but stamped at `0016_daily_bar_provenance`; no official-disclosure tables exist yet.
- Port 8000 is served by a standalone Uvicorn process started before the new router code, so OpenAPI exposes neither evidence-status nor monitor routes.
- Port 3000 is a Next development server and already renders the new frontend through hot reload.
- Redis and PostgreSQL containers are running, but no Celery worker or Beat process is active.
- The active watchlist contains no eligible six-digit A-share symbol. Acceptance therefore needs a temporary `000001:CN` canary whose original state is restored afterward.

## Requirements

- Create a timestamped PostgreSQL logical backup before applying migrations.
- Apply only the repository migration chain `0017` through `0019` and verify the resulting head and tables.
- Restart only the stale port-8000 Uvicorn process with the same host/port contract; keep port 3000 untouched.
- Start exactly one Windows-compatible Celery worker (`solo` pool) and exactly one Beat scheduler with persistent logs and PID evidence.
- Verify API health, OpenAPI route registration, evidence-status response, worker task registration, and Beat schedule registration.
- Temporarily activate `000001:CN` only when it was not already active, enqueue one bounded incremental monitor with `max_documents=1`, and observe its TaskRun to terminal state.
- Verify durable monitor state, watermark/freshness, sanitized diagnostics, bounded sequential behavior, and absence of duplicate active disclosure tasks.
- Run a second bounded incremental monitor only if needed to prove metadata/document idempotency; compare row/document counts and hashes.
- Restore the canary watchlist item to its original active/inactive/absent state after acceptance while retaining audit evidence and monitoring state.
- Preserve existing database data and leave normal API, frontend, Redis, PostgreSQL, worker, and Beat healthy at handoff.
- If a code defect is discovered, add regression tests, run the full applicable quality gate, commit, and push before continuing rollout.

## Acceptance Criteria

- [x] A restorable logical database backup exists and is non-empty.
- [x] PostgreSQL reports Alembic head `0019_official_disclosure_monitoring` and all four official-disclosure tables exist.
- [x] Port 8000 is healthy and OpenAPI contains evidence-status, watchlist-ingest, and watchlist-monitor routes.
- [x] Exactly one Celery worker and one Beat process are running and the disclosure schedule/task are registered.
- [x] A controlled `000001` incremental TaskRun reaches a terminal state with visible bounded result/diagnostics.
- [x] Monitor state persists a success cursor/freshness or a sanitized provider failure with retry checkpoint; existing evidence is never deleted.
- [x] Repeated execution does not create duplicate official metadata identities or re-download an extracted document.
- [x] The temporary canary watchlist change is restored and normal 3000/8000 services remain healthy.
- [x] Runtime evidence, commands, process IDs, task IDs, row counts, and limitations are recorded in the task directory without secrets.

## Out of Scope

- OCR, embeddings, vector search, or AI document summaries.
- Full-market disclosure crawling or more than one canary symbol/document.
- Changing user portfolio positions, alerts, recommendations, or trading state.
- Rebuilding the frontend or replacing the existing PostgreSQL/Redis containers.
