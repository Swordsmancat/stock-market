# Official disclosure evidence operations

## Goal

Make official A-share disclosure evidence operational from Evidence Center: show watchlist coverage and document status, allow one disclosure to be ingested on demand, and enqueue a bounded watchlist batch that refreshes metadata and ingests text PDFs sequentially.

## Background

- CNINFO metadata and exact-PDF section evidence already exist as separate persisted citation layers.
- Evidence Center has established server-load/client-action panels and TaskRun links for asynchronous evidence jobs.
- The default watchlist service already exposes active symbol/market entries.
- Celery TaskRun dispatch, progress heartbeats, retry links, and task-detail UI already exist.
- Historical session search found no additional product decision for this slice.

## Requirements

### R1. Watchlist disclosure coverage

- Add a read-only watchlist evidence-status API.
- Include only active six-digit `CN` watchlist instruments.
- Return symbol counts, metadata/document/section coverage, latest extracted/non-citable status, bounded disclosure rows, and sanitized diagnostics.
- Distinguish metadata-only, extracted text, no-text, rejected, failed, and never-ingested disclosures.
- Never expose local storage paths.

### R2. Single-disclosure operations

- Evidence Center lists recent persisted disclosures with official links, publication time, document status, page/section counts, and citation boundary.
- A user can ingest or re-ingest one exact disclosure from the panel through a same-origin proxy.
- Successful ingestion refreshes the page state; failures show sanitized provider/service detail.

### R3. Bounded watchlist batch

- Add an asynchronous TaskRun-backed watchlist batch endpoint.
- Request accepts a bounded lookback window and maximum document count; defaults are safe for personal use.
- Refresh CNINFO metadata for each eligible watchlist symbol, then select recent persisted disclosures deterministically.
- Ingest documents strictly one at a time and sleep between CNINFO operations using configurable delay.
- Preserve per-symbol/per-document results and diagnostics; one item failure must not discard successful evidence.
- Do not enqueue another running task of the same kind; return the active TaskRun instead.
- The batch must never widen to the full instrument universe.

### R4. Progress and failure semantics

- Update TaskRun heartbeat/progress after metadata and each document attempt.
- Final result reports requested/eligible symbols, discovered disclosures, created/unchanged/restored/non-citable/failed counts, and bounded item diagnostics.
- Provider messages remain sanitized; no response bodies, headers, secrets, filesystem paths, or stack traces enter API/TaskRun payloads.
- Empty watchlist and no-disclosure outcomes are successful `no_data` results, not fabricated coverage.

### R5. UI and compatibility

- Add a localized Evidence Center panel without displacing existing macro and market-daily evidence workflows.
- Show queued task links and explicit metadata-vs-document citation language.
- Existing disclosure APIs, assistant citations, watchlist behavior, and TaskRun pages remain backward compatible.
- Keep OCR, vectors, summaries, automated trading, and full-market crawling out of scope.

## Acceptance Criteria

- [x] Coverage API returns only eligible CN watchlist symbols and accurate metadata/document/section counts.
- [x] Coverage rows distinguish metadata-only and every non-citable/extracted document state without storage paths.
- [x] Single-document Evidence Center action proxies exact disclosure ingestion and refreshes status.
- [x] Batch endpoint enqueues a recognized Celery TaskRun and deduplicates a currently running batch.
- [x] Worker refreshes metadata and ingests at most the requested maximum, strictly sequentially with bounded delay.
- [x] Partial provider/document failures preserve successes and return sanitized per-item diagnostics.
- [x] TaskRun progress and final counters remain internally consistent for empty, partial, and successful runs.
- [x] Evidence Center renders coverage, official links, statuses, citation boundaries, batch action, single action, and task link in English and Chinese.
- [x] Backend, worker, dispatch, API proxy, component, page, lint, type, and full repository tests pass.
- [x] Executable backend/frontend specs and user documentation describe the operational boundary.

## Out of Scope

- OCR or scanned-document text recovery.
- Vector embeddings, semantic search, or document summarization.
- Scheduled automatic runs in Celery Beat.
- Full-market/universe PDF backfill.
- Parallel CNINFO document downloads.
- Non-CNINFO adapters, transcripts, paid research, or trading actions.
