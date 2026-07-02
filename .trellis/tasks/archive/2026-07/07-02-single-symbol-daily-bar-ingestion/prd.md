# Single-symbol daily-bar ingestion workflow

## Goal

Let users fetch and persist daily bars for a specific symbol, market, provider, and date range without relying on provider fixture instrument universes.

The current market snapshot ingestion path is useful for batch workflows, but it cannot reliably answer "fetch data for this symbol now" because provider `fetch_instruments()` implementations are fixture-like.

## Requirements

- Add a symbol-targeted ingestion path:
  - Accept symbol, market, optional exchange, provider, timeframe, start date, and end date.
  - Restrict the first implementation to daily bars unless a child design explicitly expands scope.
  - Dispatch work asynchronously through TaskRun/Celery in the same style as existing ingestion tasks.
- Persist fetched data:
  - Fetch bars directly by symbol through the provider adapter.
  - Upsert `Market`, `Instrument`, and `DailyBar` records idempotently.
  - Preserve existing batch market snapshot ingestion behavior.
- Return useful task metadata:
  - API response should include the created task-run id when available.
  - TaskRun input/result should include requested provider, effective provider, symbol, market, date range, inserted/updated/skipped counts, and no-data reason when applicable.
- Keep tests deterministic:
  - Use mock provider/test doubles for automated tests.
  - Do not require real provider network access in CI.

## Acceptance Criteria

- [ ] A user/API caller can enqueue single-symbol daily-bar ingestion.
- [ ] Worker/service logic persists daily bars idempotently for the requested symbol/date range.
- [ ] Existing market snapshot ingestion remains compatible.
- [ ] TaskRun records contain enough input/result detail for frontend follow-up links and diagnostics.
- [ ] Empty provider results are represented as a clear no-data outcome, not a silent success with no explanation.
- [ ] Focused API, service, and worker tests cover successful ingestion and no-data behavior.

## Suggested Validation

```powershell
python -m pytest tests/api/test_ingestion_api.py tests/services/test_ingestion_service.py tests/worker/test_tasks.py -v
python -m pytest tests/services/test_database_market_data_service.py -v
```

## Notes

- Avoid schema migration unless a concrete persistence gap is proven.
- Do not remove the existing market snapshot task.
