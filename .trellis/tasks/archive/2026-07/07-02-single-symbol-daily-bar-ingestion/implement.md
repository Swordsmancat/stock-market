# Single-symbol daily-bar ingestion workflow - Implementation Plan

## Steps

1. Add tests first for one vertical slice:
   - API dispatches `POST /ingestion/symbol-daily-bars` and persists mock daily bars through synchronous task dispatch.
2. Add the dispatch and worker task:
   - task name `ingestion.ingest_symbol_daily_bars`;
   - dispatcher entry in `packages/services/task_dispatch.py`.
3. Add the service-layer targeted ingestion function:
   - fetch provider bars directly by symbol;
   - reuse existing serialized snapshot database-writing helpers;
   - return explicit no-data metadata.
4. Add focused service and worker tests for idempotency and no-data behavior.
5. Validate focused backend targets.

## Validation

```powershell
python -m pytest tests/api/test_ingestion_api.py tests/services/test_ingestion_service.py tests/worker/test_tasks.py -v
python -m pytest tests/services/test_database_market_data_service.py -v
```

## Stop points

Pause if implementation requires:

- database schema migration;
- real provider network tests;
- changing existing market snapshot task names;
- adding non-daily timeframe semantics;
- changing provider fixture behavior globally.
