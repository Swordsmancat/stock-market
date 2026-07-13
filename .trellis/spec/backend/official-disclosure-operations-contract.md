# Official Disclosure Operations Contract

## Scenario: watchlist coverage, bounded ingestion, and incremental monitoring

### 1. Scope / Trigger

- Trigger: Evidence Center loads watchlist disclosure coverage, explicitly queues a watchlist ingestion batch, or Celery Beat/operator action queues incremental monitoring.
- Scope: `packages/services/official_disclosure_operations.py`, `OfficialDisclosureMonitorState`, migration `0019_official_disclosure_monitoring`, official-disclosure API/routes, TaskRun dispatch, and the ingestion worker/Beat schedule.
- Non-goals: universe crawling, parallel CNINFO requests, OCR, vectors, automatic summaries, notifications, investment conclusions, or trading.

### 2. Signatures

- Task: `ingestion.ingest_watchlist_official_disclosures`.
- Schedule task: `ingestion.schedule_watchlist_official_disclosures`.
- API: `GET /official-disclosures/evidence-status`, `POST /official-disclosures/watchlist/ingest`, and `POST /official-disclosures/watchlist/monitor`.
- Batch limits: lookback 1..365 days; maximum 1..50 documents; defaults 30/20.
- Configuration: `DISCLOSURE_BATCH_REQUEST_DELAY_MS`, default 1000; worker floor 250 ms.
- Monitor configuration defaults: enabled, 60-minute interval, 30-day lookback, 3-day overlap, 20 documents, 24-hour freshness SLA, and exponential retry from 60 minutes capped at 1440 minutes.

### 3. Contracts

- Scope comes only from active default-watchlist rows whose market is `CN` and symbol is six digits. Empty scope never falls back to the universe.
- Coverage distinguishes metadata-only, extracted, no-text, rejected, and failed status and never serializes `storage_path`.
- A batch refreshes metadata by symbol, then selects recent non-extracted disclosures deterministically and ingests at most the requested maximum.
- Incremental mode persists one `(source, symbol)` state containing a `(published_at, source_document_id)` watermark, lifecycle timestamps, retry state, sanitized diagnostic, and last-run new count.
- The watermark is observable state, not an exclusive fetch boundary. Incremental mode queries from `max(lookback start, cursor date - overlap)`; official source identity remains the metadata dedupe authority.
- Success advances the watermark to the newest persisted official row and clears retry state. Failure preserves the previous watermark and schedules bounded exponential backoff. Scheduled mode skips symbols whose `next_retry_at` is in the future; explicit batch mode may retry them.
- The Evidence Center freshness projection uses `fresh`, `stale`, `backoff`, and `never` states. A new-disclosure count is a human research-review signal only.
- Every CNINFO metadata/document operation runs in one synchronous worker loop. No child tasks, futures, or concurrent downloads are allowed.
- A delay is applied between external calls. Scheduled and explicit paths use the same task name and return one active TaskRun instead of dispatching a concurrent batch.
- A disclosure whose latest document is already `extracted` is never selected for repeat download.
- Per-item provider failures are sanitized and do not roll back previously committed evidence.
- TaskRun progress updates after every symbol and document attempt. Empty scope/candidates produce `no_data`; mixed results produce `partial`.

### 4. Validation & Error Matrix

- Invalid request limit -> API 422.
- Active batch -> HTTP 200 with `status=already_running` and existing TaskRun.
- Scheduled symbol in retry window -> no external call for that symbol and explicit `backoff` state.
- Empty watchlist -> succeeded TaskRun with `status=no_data`.
- Provider/document failure -> bounded diagnostic with source, stage, symbol, code, and sanitized message.
- Unexpected worker exception -> failed TaskRun; no raw provider response is persisted.

### 5. Good / Base / Bad Cases

- Good: two eligible symbols refresh sequentially and only missing text PDFs are ingested.
- Good: an incremental refresh overlaps the durable cursor, receives repeated same-timestamp rows, and advances only to the newest persisted official identity without duplicate downloads.
- Base: one symbol fails schema validation, retains its previous cursor, and is skipped until retry while another symbol remains successful and fresh.
- Base: no A-share watchlist symbols returns zero coverage and no external calls.
- Base: one PDF fails while another succeeds; success remains stored and result is partial.
- Bad: querying the enriched watchlist payload triggers an unrelated quote provider before CNINFO work.
- Bad: empty watchlist widens to all A shares or two batches download concurrently.

### 6. Tests Required

- Service tests cover eligibility, coverage counts, storage-path redaction, deterministic limits, delays, no-data, partial failure, cursor overlap/advance, retry preservation/backoff, freshness, extracted-document dedupe, and active-run reuse.
- API/dispatch/worker tests cover both operator routes, Celery mapping/schedule, progress, mutex reuse, and final TaskRun state.
- Migration tests assert the monitor table, cursor/retry columns, index, foreign key, and unique source/symbol identity.
- Tests inject provider/document functions and never call live CNINFO.

### 7. Wrong vs Correct

Wrong: fan out one Celery task per document or use the full instrument universe when the watchlist is empty.

```python
symbols = universe_symbols if not watchlist_symbols else watchlist_symbols
group(ingest_document.s(symbol) for symbol in symbols).delay()
```

Correct: read `get_active_watchlist_scope()`, loop synchronously with a bounded delay, persist each result idempotently, and report progress through the owning TaskRun.

```python
symbols = eligible_cn_symbols(get_active_watchlist_scope(session))
for disclosure in pending_disclosures(symbols)[:max_documents]:
    sleep_between_external_calls()
    ingest_official_disclosure_document(str(disclosure.id), session=session)
    report_progress()
```
