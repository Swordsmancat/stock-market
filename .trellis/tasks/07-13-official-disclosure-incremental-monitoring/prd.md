# Official disclosure incremental monitoring

## Goal

Continuously refresh official CNINFO disclosures for active A-share watchlist symbols without repeated document downloads, while making per-symbol freshness, retry state, and newly discovered evidence visible to research users and operators.

## Background

- The existing Evidence Center can run an explicit bounded watchlist ingestion TaskRun and ingest exact PDFs sequentially.
- Metadata upserts are idempotent by official source document identity, and extracted PDF versions are content-addressed.
- The current operation always uses a fixed lookback and has no durable per-symbol cursor, scheduled refresh, retry state, or freshness/SLA reporting.
- The active watchlist is the operational boundary; full-market crawling remains excluded.

## Requirements

- Persist one CNINFO monitoring state per eligible A-share watchlist symbol, including a publication/document cursor, last attempt/success/failure, consecutive failures, next retry, last sanitized diagnostic, and number of newly discovered disclosures in the last successful run.
- Treat the cursor as an observable watermark, not an exclusive provider boundary: incremental refreshes must use a bounded overlap window so late, corrected, or same-timestamp announcements remain discoverable and database identity deduplication remains authoritative.
- Schedule bounded incremental refreshes through Celery Beat and expose an operator action to enqueue the same mode immediately.
- Reuse the existing TaskRun pipeline and active-run mutex so manual batches and scheduled monitoring cannot execute concurrent CNINFO watchlist backfills.
- Skip symbols still inside exponential backoff during scheduled incremental runs; explicit bounded ingestion may bypass backoff for operator recovery.
- Download only disclosures whose latest document is absent or not successfully extracted; never re-download already extracted document versions.
- Report monitoring freshness against a configurable SLA, including fresh, stale, retry-backoff, and never-succeeded symbol counts and per-symbol status.
- Surface the last-run new-disclosure count in Evidence Center as a research review signal. Do not automatically generate investment conclusions, recommendations, or trades.
- Keep CNINFO requests sequential, bounded, rate-limited, and restricted to active six-digit CN watchlist symbols.
- Sanitize provider/persistence diagnostics and preserve successful symbols and existing evidence when another symbol fails.

## Acceptance Criteria

- [x] A migration and ORM model persist independent monitoring state for each eligible symbol.
- [x] A successful incremental run advances the durable watermark and freshness state; a failed run preserves the previous watermark and records bounded exponential retry state.
- [x] Incremental metadata refresh uses a configurable overlap window and remains idempotent for same-timestamp or repeated provider results.
- [x] Scheduled and operator-triggered monitoring share the existing TaskRun mutex, and only one CNINFO watchlist backfill can be active.
- [x] Already extracted PDFs are not selected for download again.
- [x] Celery Beat contains a configurable incremental watchlist disclosure schedule with bounded defaults.
- [x] `GET /official-disclosures/evidence-status` returns aggregate and per-symbol monitoring freshness without leaking storage paths or secrets.
- [x] An operator endpoint and Evidence Center control can enqueue incremental monitoring and link to the resulting TaskRun.
- [x] Backend, worker, migration, API, proxy, component, localization, and full regression checks pass.
- [x] Documentation preserves official-source, source-rights, citation, research-only, and no-automated-trading boundaries.

## Out of Scope

- Full-market or unbounded disclosure crawling.
- OCR, embeddings, vector search, or AI summarization.
- Licensed research and transcript ingestion.
- Automatic buy/sell/hold conclusions, target prices, position sizing, notifications, or trading execution.
