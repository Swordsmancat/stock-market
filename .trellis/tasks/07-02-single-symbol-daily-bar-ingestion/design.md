# Single-symbol daily-bar ingestion workflow - Design

## Summary

The existing ingestion workflow is market-snapshot based. It asks the provider for its instrument universe and then fetches bars for those fixture instruments. That is not enough for a user-driven product flow where a user enters one symbol and expects the platform to fetch and persist that symbol's daily bars.

This task adds a targeted daily-bar ingestion path while preserving the existing market snapshot endpoints and worker task.

## Target workflow

```text
API caller submits symbol + market + date range + optional provider
  -> ingestion router enqueues a TaskRun for ingestion.ingest_symbol_daily_bars
  -> task dispatcher calls the Celery worker task with task_run_id
  -> worker parses dates and provider, then calls ingestion service
  -> service fetches provider bars directly by symbol
  -> service upserts Market, Instrument, and DailyBar rows
  -> worker stores TaskRun result with symbol, market, provider, bar_count, and no_data_reason
  -> API returns the TaskRun payload so the frontend can link to task status
```

## API design

Add a new endpoint under the existing ingestion router:

- `POST /ingestion/symbol-daily-bars`

Query parameters:

- `symbol`: required, normalized to uppercase before task input is stored.
- `market`: required, normalized to uppercase before task input is stored.
- `provider`: optional. Omitted provider should be passed through as `None` so platform settings can choose the effective provider.
- `start`: required ISO date.
- `end`: required ISO date.
- `exchange`: optional string.
- `timeframe`: optional, default `1d`. The first implementation only accepts `1d`.

The response should reuse `enqueue_task_run()` and therefore match existing async ingestion responses:

```json
{
  "source": "database",
  "status": "dispatched",
  "task_run": { "id": "...", "task_name": "ingestion.ingest_symbol_daily_bars", ... },
  "celery_task_id": "..."
}
```

## Service design

Add a service function in `packages/services/ingestion.py`:

- `ingest_symbol_daily_bars(symbol, market, start, end, session=None, provider_name=None, exchange=None, timeframe="1d")`

Responsibilities:

- Reject unsupported timeframes with `ValueError`.
- Resolve the effective provider via the existing market-data provider resolution path.
- Fetch bars directly via `provider.fetch_bars(symbol, "1d", start, end)`; do not call `fetch_instruments()`.
- Build a serialized single-instrument snapshot so existing parsing, upsert, bar counting, and quality diagnostics helpers can be reused.
- Upsert market/instrument/daily bars when a session is supplied.
- Return a stable summary containing:
  - `status`: `ingested` when bars were returned, `no_data` when provider returned no bars;
  - `symbol`, `market`, `provider`, `requested_provider`, `effective_provider`;
  - `timeframe`, `start`, `end`, `bar_count`, `instrument_count`;
  - `no_data_reason` for empty provider results;
  - `quality_diagnostics`.

The service should not introduce a database migration. It can create an `Instrument` with the provided symbol, symbol as fallback name, `asset_type="stock"`, and the market currency from `MARKET_META`.

## Worker and TaskRun design

Add a new Celery task:

- task name: `ingestion.ingest_symbol_daily_bars`

The task should mirror `ingestion.ingest_market_data` lifecycle behavior:

- reuse an existing TaskRun when `task_run_id` is passed;
- create its own TaskRun when called directly;
- call `finish_task_run()` on success;
- call `fail_task_run()` and re-raise on failure;
- close its session in `finally`.

The task result should include enough fields for frontend follow-up and diagnostics without requiring a second database query.

## Dispatch design

Add a dispatcher in `packages/services/task_dispatch.py` so `enqueue_task_run()` can dispatch the new task by name.

## Compatibility

- Existing `/ingestion/snapshot` and `/ingestion/mock-snapshot` behavior must remain unchanged.
- Existing `ingestion.ingest_market_data` task remains available.
- Existing market snapshot quality diagnostics remain unchanged.

## Test design

- API test: `POST /ingestion/symbol-daily-bars` dispatches a task, writes rows in synchronous-Celery test mode, and returned market-data bars come from the database.
- Service test: targeted ingestion fetches provider bars without `fetch_instruments()` and is idempotent on repeated runs.
- Service test: empty provider bars return `status="no_data"` with a no-data reason and no daily rows.
- Worker test: worker stores a succeeded TaskRun result for symbol ingestion.

No tests should require real provider network access.
