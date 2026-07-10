# A-share Live Acceptance Design

## Runtime Boundary

```text
host runner -> read-only AkShare preflight
            -> stock-acceptance Compose project
               -> stock_acceptance PostgreSQL volume
               -> isolated Redis
               -> API -> Celery worker/beat -> AkShare
               -> Web -> acceptance API
            -> sanitized task evidence artifacts
```

- `docker-compose.acceptance.yml` is self-contained and uses dedicated host ports so the normal stack can coexist.
- The acceptance runner talks only to the configured acceptance API. It validates `/health`, then a sanitized runtime-info endpoint/command and the database name before mutations.
- Compose commands always use project name `stock-acceptance`; cleanup never names or removes the normal `pgdata` volume.

## Runner Contract

- Default behavior is non-mutating metadata/preflight.
- Mutating phases require both `--real-network` and `--confirm-acceptance-writes`.
- `--database-name stock_acceptance` is required and cross-checked against a PostgreSQL connection or the isolated API runtime.
- HTTP helpers keep bounded timeouts and payload-size limits; polling has explicit deadline and terminal statuses.
- Artifacts pass a recursive redactor for URL credentials, secret-like keys, bearer/cookie/header values, and raw exception bodies before JSON/Markdown writes.
- Findings use `product_defect`, `provider_limitation`, `environment_configuration`, or `accepted_data_gap`.

## Execution Order

1. Capture clean commit/dependency/migration metadata and run non-mutating preflight.
2. Start/verify isolated DB, Redis, API, worker, beat, and Web.
3. Dispatch universe sync through the public API and verify reconciliation/exchanges.
4. Start the deterministic 50-symbol backfill canary; poll authoritative coverage and TaskRun state.
5. Exercise corporate-action cursor batches and idempotent replay.
6. Execute the three discovery profiles twice with LLM fallback and compare membership/ranking.
7. Browser-smoke AI Research, Evidence Center, and TaskRun at desktop/mobile widths.
8. Start full baseline only after the canary supports it; monitor checkpoints and stop safely on provider-wide failure.
9. Write sanitized report/runbook, implement only demonstrated product defects with regression tests, and rerun affected slices.

## Rollback and Retention

- `docker compose -p stock-acceptance -f docker-compose.acceptance.yml down` stops services and retains acceptance volumes.
- `down --volumes` is a separately documented destructive cleanup limited to project-prefixed acceptance volumes.
- Cancel preserves completed batches/checkpoints. No script deletes evidence or the normal database.
