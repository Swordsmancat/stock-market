# Rollout design

## Safety boundaries

- Back up before DDL. Validate backup size and checksum without printing credentials.
- Use the configured local database connection and repository Alembic environment; do not stamp or skip revisions.
- Restart only the process owning port 8000 after migration succeeds. Do not stop port 3000.
- Run Worker and Beat as hidden background processes with separate PID/log files under task-local evidence.
- Never start a second Beat instance; inspect existing process command lines and PID files before launch.

## Rollout sequence

1. Capture preflight: Git SHA, ports/PIDs, database revision/table counts, watchlist state, Redis/PostgreSQL health.
2. Produce a compressed custom-format `pg_dump` inside the database container and copy it to task-local evidence; compute SHA-256.
3. Run `alembic upgrade head`, then verify revision, schema, constraints, and existing-row counts.
4. Stop the old Uvicorn PID and launch the same app on `127.0.0.1:8000`; poll `/health` and OpenAPI.
5. Launch a single `solo` Celery worker and a single Beat process; verify broker ping, registered disclosure tasks, and configured schedule.
6. Snapshot the `000001:CN` watchlist state, activate it if necessary, enqueue an incremental monitor through the HTTP API, and poll its TaskRun.
7. Audit official metadata/document/section/monitor-state rows and TaskRun result. If successful, run one bounded repeat to prove idempotency; if provider-wide failure occurs, preserve checkpoint/backoff evidence and do not widen scope.
8. Restore the canary watchlist state and run final health/process/database checks.

## Rollback

- Migration failure: PostgreSQL transactional DDL should retain the prior revision; stop and preserve logs/backup.
- API launch failure: stop the failed replacement and restart the previous command against the migrated compatible schema.
- Worker/Beat failure: stop only newly created PIDs; API/frontend/database remain available.
- Data-corruption evidence: stop monitor processes and restore from the logical backup only after confirming restoration scope; do not automatically overwrite the database during acceptance.

## Evidence boundary

- Store command outcomes, counts, IDs, timestamps, and sanitized provider diagnostics.
- Do not store database URLs, passwords, raw provider responses, or document bodies in task evidence.
