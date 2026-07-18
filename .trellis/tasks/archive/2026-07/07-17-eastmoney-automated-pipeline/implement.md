# Eastmoney automated pipeline implementation

1. Read worker, TaskRun, provider, storage, settings, database, and crawler
   monitor specs; lock stable task names, bounds, and safe diagnostics in tests.
2. Add environment-backed enable/schedule/batch/delay/retry settings with
   conservative defaults and configuration tests.
3. Add the bounded active research-universe resolver with watchlist/latest-
   shortlist deduplication and focused SQLite tests.
4. Add a dedicated write-specific Eastmoney fundamentals/company persistence
   service; add an additive model/migration only if existing storage cannot
   truthfully own normalized company metadata.
5. Add four service batch operations with sequential pacing, provider error
   classification, progress callbacks, overlap protection, and preservation of
   stored evidence on failure.
6. Add four Celery tasks with complete TaskRun lifecycle handling, safe replay,
   progress heartbeats, and worker tests.
7. Register four Beat schedules and dispatch mappings; test enabled/disabled
   schedules and ensure they do not collide with existing A-share jobs.
8. Extend the crawler monitor backend/frontend contract, translations,
   navigation tests, and responsive status rendering for the new pipelines.
9. Run focused Ruff/pytest/Vitest/TypeScript checks, then full backend/frontend
   suites and Trellis Check. Scan TaskRun/API payloads for secret leakage.
10. Rebuild/restart only API/Web/Worker/Beat as required, verify PostgreSQL and
    Redis health, observe one bounded live run per pipeline without overlap, and
    confirm the normal 3000/8000 stack remains available.
11. Update the durable Eastmoney automation contract and operational runbook;
    leave commit/push/archive work pending unless explicitly requested.

## Rollback Points

- Settings/schedule registration can be disabled before any live provider run.
- Each service batch is independently testable before worker registration.
- Monitor entries are additive and can be reverted without affecting workers.
- Any migration must be reversible and must not rewrite existing evidence.
