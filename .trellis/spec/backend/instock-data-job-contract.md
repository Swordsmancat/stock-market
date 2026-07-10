# InStock-Inspired Data Job Contract

## Scenario: Single-Symbol Daily Stock / ETF Ingestion

### 1. Scope / Trigger

- Trigger: `POST /ingestion/symbol-daily-bars` enqueues a targeted daily-bar
  ingestion job for one instrument.
- Scope: FastAPI route in `apps/api/routers/ingestion.py`, task dispatch in
  `packages/services/task_dispatch.py`, Celery worker in
  `apps/worker/tasks/ingestion.py`, service persistence in
  `packages/services/ingestion.py`, and focused API/service/worker tests.
- Non-goals: provider-specific ETF universe crawling, InStock scheduler import,
  proxy/cookie scraping, MySQL/Tornado runtime, strategy execution, broker
  orders, or automatic trading.

### 2. Signatures

- API:
  `POST /ingestion/symbol-daily-bars`
- Query fields:
  - `symbol`
  - `market`
  - `provider`
  - `start`
  - `end`
  - `exchange`
  - `timeframe`, currently only `1d`
  - `asset_type`, default `stock`, supported values `stock` and `etf`
- Task name:
  `ingestion.ingest_symbol_daily_bars`
- Service entry:
  `ingest_symbol_daily_bars(..., asset_type="stock")`

### 3. Contracts

- The route must normalize `symbol` and `market` before writing TaskRun input.
- `asset_type` must flow through TaskRun input, Celery task kwargs, worker
  result payload, serialized snapshot instrument payload, and persisted
  `Instrument.asset_type`.
- The provider boundary still fetches bars by symbol/timeframe/date only; this
  slice does not require provider universe support for ETFs.
- Supported `asset_type` values are `stock` and `etf`. Empty values default to
  `stock`.
- Stored daily bars remain ordinary `DailyBar` rows keyed by instrument/date.
- Payloads must not emit buy/sell/hold actions, target prices, position sizing,
  order intents, broker routing, or execution instructions.

### 4. Validation & Error Matrix

- Unsupported timeframe -> service `ValueError`, failed task-run when executed
  through Celery.
- Unsupported `asset_type` -> service `ValueError` before provider fetch and no
  instrument row written.
- Provider returns no bars -> `status="no_data"`, `bar_count=0`, and no daily
  rows fabricated.
- Duplicate symbol/date rows -> one stored daily row, last processed serialized
  value wins, while processed count still reflects input bars.

### 5. Good/Base/Bad Cases

- Good: `POST /ingestion/symbol-daily-bars?symbol=SPY&market=US&asset_type=etf...`
  stores `Instrument(symbol="SPY", asset_type="etf")` when provider bars exist.
- Base: omitting `asset_type` stores the instrument as `stock`, preserving the
  previous behavior.
- Bad: the endpoint scans an ETF universe from a provider when a single-symbol
  job was requested.
- Bad: InStock scheduler/database modules are imported to run the job.
- Bad: an ingested ETF row is treated as a recommendation or order candidate.

### 6. Tests Required

- Service tests assert `asset_type="etf"` is persisted and unsupported values
  fail before provider fetch.
- API tests assert TaskRun input and worker result payload include `asset_type`.
- Dispatch tests assert Celery kwargs include `asset_type`.
- Worker tests assert succeeded task-runs persist `asset_type` in input/result.
- Focused validation should include:
  `pytest tests/services/test_ingestion_service.py tests/api/test_ingestion_api.py tests/services/test_task_dispatch.py tests/worker/test_tasks.py`,
  ruff on touched Python files, and `git diff --check`.

### 7. Wrong vs Correct

#### Wrong

```python
"asset_type": "stock"
```

Hard-coding stock in the serialized single-symbol snapshot loses ETF identity.

#### Correct

```python
"asset_type": normalized_asset_type
```

The explicit API/task value survives into the persisted instrument row.

## Scenario: Batch Symbol Daily Stock / ETF Ingestion

### 1. Scope / Trigger

- Trigger: `POST /ingestion/symbol-daily-bars-batch` enqueues targeted daily-bar
  ingestion for an explicit comma-separated symbol list.
- Scope: FastAPI route in `apps/api/routers/ingestion.py`, task dispatch in
  `packages/services/task_dispatch.py`, Celery worker in
  `apps/worker/tasks/ingestion.py`, batch helper in
  `packages/services/ingestion.py`, synchronous Celery test helper, and focused
  API/service/dispatch/worker tests.
- Non-goals: scanning provider universes, importing InStock schedulers, running
  crawlers/proxy/cookie workflows, strategy execution, order intents, broker
  calls, or automatic trading.

### 2. Signatures

- API:
  `POST /ingestion/symbol-daily-bars-batch`
- Query fields:
  - `symbols`, comma-separated and deduped after trim/upper normalization
  - `market`
  - `provider`
  - `start`
  - `end`
  - `exchange`
  - `timeframe`, currently only `1d`
  - `asset_type`, default `stock`, supported values `stock` and `etf`
- Task name:
  `ingestion.ingest_symbol_daily_bars_batch`
- Service entries:
  - `normalize_symbol_list(symbols)`
  - `ingest_symbol_daily_bars_batch(..., asset_type="stock")`

### 3. Contracts

- The API route must normalize and dedupe `symbols` before writing TaskRun
  input, so `["AAPL", "MSFT"]` is the persisted contract instead of a raw comma
  string.
- The worker must preserve the normalized symbol list in TaskRun input and
  result payloads.
- The batch helper must reuse `ingest_symbol_daily_bars(...)` for each explicit
  symbol, preserving the single-symbol storage path and quality diagnostics.
- Batch results include `symbol_count`, `succeeded_count`, `no_data_count`,
  `failed_count`, `total_bar_count`, `items[]`, and `diagnostics[]`.
- Per-symbol provider failures are captured as item-level failures and batch
  diagnostics; they do not erase already persisted successful symbols.
- Empty symbol lists, unsupported timeframe, and unsupported `asset_type` are
  task-level invalid input and must fail before provider fetch.
- Payloads must not emit buy/sell/hold actions, target prices, position sizing,
  order intents, broker routing, or execution instructions.

### 4. Validation & Error Matrix

- Empty `symbols` -> API HTTP 400 before dispatch; service/worker `ValueError`
  before provider fetch.
- Duplicate symbols -> one fetch per normalized symbol, preserving request
  order.
- Unsupported timeframe -> service `ValueError` before provider fetch and failed
  task-run when executed through Celery.
- Unsupported `asset_type` -> service `ValueError` before provider fetch and no
  instrument row written for the batch.
- Provider returns no bars for one symbol -> that item has `status="no_data"`,
  `bar_count=0`, and increments `no_data_count`.
- Provider raises for one symbol -> that item has `status="failed"`, increments
  `failed_count`, and adds a sanitized diagnostic without secrets.
- Mixed outcomes -> batch result `status="partial"` while TaskRun can still
  succeed because the batch orchestration completed.

### 5. Good/Base/Bad Cases

- Good:
  `POST /ingestion/symbol-daily-bars-batch?symbols=SPY,QQQ&market=US&asset_type=etf...`
  stores two ETF instruments when provider bars exist.
- Base: `symbols=aapl,AAPL,msft` writes TaskRun input
  `["AAPL", "MSFT"]` and fetches each normalized symbol once.
- Bad: the endpoint scans all ETFs or all stocks from a provider because a batch
  route was requested.
- Bad: one provider exception aborts the whole batch after earlier symbols have
  succeeded, losing item-level diagnostics.
- Bad: a batch ingestion result is treated as a recommendation, watchlist
  mutation, or order candidate.

### 6. Tests Required

- Service tests assert symbol normalization/dedupe, partial success/no-data/fail
  counts, per-symbol diagnostics, and no provider instrument-universe fetch.
- Service tests assert empty symbols fail before provider fetch.
- API tests assert TaskRun input stores normalized symbols and sync execution
  writes bars for multiple symbols.
- Dispatch tests assert Celery kwargs include `symbols`, `asset_type`,
  `timeframe`, and optional provider/exchange.
- Worker tests assert succeeded TaskRun result payloads include normalized
  symbols and batch counts.
- Focused validation should include:
  `pytest tests/services/test_ingestion_service.py tests/api/test_ingestion_api.py tests/services/test_task_dispatch.py tests/worker/test_tasks.py`,
  ruff on touched Python files, and `git diff --check`.

### 7. Wrong vs Correct

#### Wrong

```python
for instrument in provider.fetch_instruments(market):
    ingest_symbol_daily_bars(instrument.symbol, ...)
```

This turns an explicit-symbol batch job into a provider-universe crawler.

#### Correct

```python
for symbol in normalize_symbol_list(symbols):
    ingest_symbol_daily_bars(symbol=symbol, ...)
```

Only user-requested symbols are ingested, through the existing single-symbol
storage contract.

## Universe and Corporate-Action Job Addendum

- `ingestion.sync_instrument_universe` calls the separate
  `fetch_instrument_universe("CN")` provider path, records TaskRun progress, and
  never routes the full universe through snapshot-plus-bars ingestion.
- A complete universe snapshot may deactivate missing rows managed by the same
  provider. Empty, incomplete, provider-failed, or schema-failed snapshots
  deactivate nothing and preserve manual rows.
- `ingestion.sync_corporate_actions` accepts ISO `report_period`, normalized
  symbols/event types, `cursor>=0`, and `batch_size=1..100`.
- Corporate-action batches preserve partial success, expose `next_cursor`, and
  store `failed_event_types`, `degraded_event_types`, and `failed_symbols` for
  deterministic retry.
- TaskRun progress lives in `result_json.progress` while running and the final
  service result replaces it with a completed progress payload.
- See [Comprehensive A-share Research Coverage Contract](./a-share-research-coverage-contract.md)
  for validation/error cases and end-to-end test assertions.
- Full-universe evidence population is a separate resumable task named
  `ingestion.backfill_a_share_research_evidence`; do not extend the explicit-
  symbol batch endpoint into a hidden universe crawler. Its checkpoint,
  heartbeat, error, coverage, and scheduling contract is defined in the linked
  comprehensive A-share spec.
