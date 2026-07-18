# ETF and Index Ingestion Implementation Plan

## Ordered Work

- [x] Add focused failing tests for ETF/index provider catalogs and asset-aware bar routing.
- [x] Extend provider and universe service contracts with backward-compatible `asset_type` defaults.
- [x] Add the sync-history migration/model field and migration regression coverage.
- [x] Add the bounded pipeline service/worker with sequential progress and overlap protection.
- [x] Add generic dispatch, manual ingestion API, Beat schedule, and crawler-monitor classification.
- [x] Run focused provider/service/API/worker/migration tests.
- [x] Run Trellis Check and the relevant full backend suite.
- [x] Perform a live local pipeline acceptance without interrupting ports 3000/8000; record counts and sanitized failures.
- [x] Update the backend executable contract, finish the Trellis task, commit, and push when credentials/history allow a non-destructive push.

## Validation Commands

```powershell
pytest tests/providers/test_cn_market_providers.py tests/services/test_instrument_universe.py tests/services/test_ingestion_service.py
pytest tests/worker/test_tasks.py tests/worker/test_celery_schedule.py tests/services/test_task_dispatch.py tests/services/test_crawler_monitor_service.py tests/api/test_ingestion_api.py tests/domain/test_migrations.py
pytest tests
python ./.trellis/scripts/task.py check 07-19-etf-index-ingestion
```

## Risk and Rollback Points

- Provider schema drift: adapters reject malformed frames with stable diagnostics; tests use injected frames and never require network.
- Identity collision: never mutate a stored symbol from stock to ETF/index; surface a deterministic diagnostic/failure.
- Provider rate limiting: one synchronous loop, explicit delay, bounded window, no child tasks.
- Long initial run: TaskRun heartbeat/progress makes partial completion visible and committed upserts make reruns idempotent.
- Schedule regression: new entry is additive and can be disabled independently without touching the existing stock or research schedules.
