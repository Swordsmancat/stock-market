# Official Disclosure Operations Contract

## Scenario: watchlist coverage and bounded sequential ingestion

### 1. Scope / Trigger

- Trigger: Evidence Center loads watchlist disclosure coverage or explicitly queues a watchlist ingestion batch.
- Scope: `packages/services/official_disclosure_operations.py`, official-disclosure API routes, TaskRun dispatch, and the ingestion worker.
- Non-goals: Celery Beat scheduling, universe crawling, parallel CNINFO requests, OCR, vectors, summaries, or trading.

### 2. Signatures

- Task: `ingestion.ingest_watchlist_official_disclosures`.
- API: `GET /official-disclosures/evidence-status` and `POST /official-disclosures/watchlist/ingest`.
- Batch limits: lookback 1..365 days; maximum 1..50 documents; defaults 30/20.
- Configuration: `DISCLOSURE_BATCH_REQUEST_DELAY_MS`, default 1000; worker floor 250 ms.

### 3. Contracts

- Scope comes only from active default-watchlist rows whose market is `CN` and symbol is six digits. Empty scope never falls back to the universe.
- Coverage distinguishes metadata-only, extracted, no-text, rejected, and failed status and never serializes `storage_path`.
- A batch refreshes metadata by symbol, then selects recent non-extracted disclosures deterministically and ingests at most the requested maximum.
- Every CNINFO metadata/document operation runs in one synchronous worker loop. No child tasks, futures, or concurrent downloads are allowed.
- A delay is applied between external calls. One active TaskRun is returned instead of dispatching a duplicate batch.
- Per-item provider failures are sanitized and do not roll back previously committed evidence.
- TaskRun progress updates after every symbol and document attempt. Empty scope/candidates produce `no_data`; mixed results produce `partial`.

### 4. Validation & Error Matrix

- Invalid request limit -> API 422.
- Active batch -> HTTP 200 with `status=already_running` and existing TaskRun.
- Empty watchlist -> succeeded TaskRun with `status=no_data`.
- Provider/document failure -> bounded diagnostic with source, stage, symbol, code, and sanitized message.
- Unexpected worker exception -> failed TaskRun; no raw provider response is persisted.

### 5. Good / Base / Bad Cases

- Good: two eligible symbols refresh sequentially and only missing text PDFs are ingested.
- Base: no A-share watchlist symbols returns zero coverage and no external calls.
- Base: one PDF fails while another succeeds; success remains stored and result is partial.
- Bad: querying the enriched watchlist payload triggers an unrelated quote provider before CNINFO work.
- Bad: empty watchlist widens to all A shares or two batches download concurrently.

### 6. Tests Required

- Service tests cover eligibility, coverage counts, storage-path redaction, deterministic limits, delays, no-data, partial failure, and active-run reuse.
- API/dispatch/worker tests cover route validation, Celery mapping, progress, and final TaskRun state.
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
