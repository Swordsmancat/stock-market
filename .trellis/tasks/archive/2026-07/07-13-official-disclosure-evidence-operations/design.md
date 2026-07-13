# Design: official disclosure evidence operations

## Architecture

```text
Evidence Center server page
  -> GET /official-disclosures/evidence-status
  -> watchlist + disclosure/document aggregate service
  -> localized client panel
       -> POST /api/official-disclosures/{id}/ingest-document
       -> POST /api/official-disclosures/watchlist-ingest
            -> backend enqueue TaskRun (dedupe active task)
            -> Celery worker
                 -> eligible default-watchlist A shares
                 -> sequential metadata refresh per symbol
                 -> deterministic recent disclosure selection
                 -> sequential exact-PDF ingestion + configured delay
                 -> TaskRun progress/final result
```

## Backend contracts

- Task name: `ingestion.ingest_watchlist_official_disclosures`.
- Batch input: `lookback_days` (1..365, default 30), `max_documents` (1..50, default 20), and optional request delay constrained by server configuration.
- Configuration: `DISCLOSURE_BATCH_REQUEST_DELAY_MS`, default 1000 and clamped to a safe minimum by execution.
- Coverage endpoint: `GET /official-disclosures/evidence-status?limit=1..200`.
- Batch endpoint: `POST /official-disclosures/watchlist/ingest`.
- Existing `POST /official-disclosures/{id}/ingest-document` remains the single-item operation.

## Selection and sequencing

Eligible entries are unique active watchlist rows with market `CN` and a six-digit A-share symbol. Metadata refresh uses `[today-lookback_days, today]` for each symbol. Candidate disclosures are then read from persisted rows within the same window, ordered by publication time descending, symbol ascending, and stable announcement identity. At most `max_documents` candidates are ingested.

The implementation uses normal synchronous calls in one worker loop; it never creates child Celery jobs or concurrent futures. A delay is applied between external CNINFO operations. A running TaskRun of the same task name is returned rather than dispatching a duplicate.

## Coverage payload

Summary contains eligible symbol count, metadata disclosure count, disclosures with documents, extracted document count, citable section count, metadata-only count, and non-citable count. Items include disclosure identity, symbol/title/category/published/source URL, metadata citation ID, latest document public metadata, section count, content citation availability, and a status enum. Storage paths are absent.

## Failure and safety

Per-symbol metadata errors and per-document ingestion errors become bounded sanitized diagnostics and failed item records; processing continues. Unexpected worker failure marks TaskRun failed. Empty watchlists/no candidates return `no_data`. Task payloads never include provider response bodies or local paths.

## Frontend

A dedicated client component follows the existing market-daily evidence panel pattern. The Evidence Center server page loads initial status. The component exposes one batch button, individual ingest buttons, official source links, coverage metrics, status badges, citation boundary copy, errors, and TaskRun link. User-visible copy lives in both locale files.

## Compatibility and rollback

All routes, task mappings, component, config, and docs are additive; no migration is needed. Removing the panel/task leaves existing metadata/document evidence intact. No automatic Beat schedule is introduced.
