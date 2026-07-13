# Execution plan

1. Validate clean Git state and capture preflight runtime evidence.
2. Create and verify a timestamped PostgreSQL backup.
3. Apply Alembic `0017..0019` and verify schema/head.
4. Restart Uvicorn on port 8000 and verify official-disclosure routes.
5. Start one Celery worker and one Beat process with task-local logs.
6. Verify Redis ping, worker task registration, Beat schedule, and process uniqueness.
7. Snapshot/activate temporary `000001:CN`, enqueue bounded incremental monitoring, and poll TaskRun.
8. Audit cursor, retry/freshness, disclosure/document dedupe, source identity, and diagnostics.
9. Restore the canary watchlist state and run final 3000/8000/process/database checks.
10. If code changes were required, run focused and full checks, update specs, commit, push, and resume rollout.
11. Record sanitized evidence, complete Trellis Check, archive the task, and record the session.

## Validation commands

- `python -m alembic current`
- read-only SQLAlchemy schema/count inspection
- `GET /health`, `GET /openapi.json`, `GET /official-disclosures/evidence-status`
- `celery inspect ping` and `celery inspect registered`
- TaskRun API polling plus database verification
- final port/process uniqueness and Git cleanliness checks

## Start gate

- The user explicitly approved the recommended rollout and acceptance sequence.
- The temporary canary is restored after verification.
- No unresolved product-intent question blocks execution.
