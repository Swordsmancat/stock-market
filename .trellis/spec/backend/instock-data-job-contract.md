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
