# Bug Analysis: Alembic Version Column Blocked Frontend Data

### 1. Root Cause Category

- **Category**: D/E — Test Coverage Gap and Implicit Assumption
- **Specific cause**: PostgreSQL enforced Alembic's legacy
  `alembic_version.version_num VARCHAR(32)`, but migration revision
  `0010_intraday_minute_cache_entries` is longer than 32 characters. The
  migration DDL rolled back when Alembic could not persist the revision ID,
  leaving the normal database on `0009` while the API code expected `0015`.

### 2. Why Earlier Recovery Failed

1. Starting the frontend fixed the connection-refused symptom but exposed the
   separate API/data failure.
2. The first combined “upgrade then start API” PowerShell command continued to
   the final process-start command, so its overall exit status hid the failed
   migration. A dedicated migration command exposed the truncation error.
3. Existing SQLite migration tests could not reproduce PostgreSQL's enforced
   `VARCHAR(32)` limit.

### 3. Prevention Mechanisms

| Priority | Mechanism | Specific action | Status |
|---|---|---|---|
| P0 | Runtime compatibility | Widen legacy PostgreSQL version columns to 128 before Alembic migration context starts | DONE |
| P0 | Regression test | Assert widening/no-op behavior and bound every repository revision ID | DONE |
| P1 | Documentation | Record the contract and diagnosis commands in backend database guidelines | DONE |
| P1 | Operational check | Treat `alembic current` plus table inspection as authoritative, not `alembic heads` | DONE |

### 4. Systematic Expansion

- **Similar issues**: Any database created before descriptive migration IDs can
  fail on the first revision longer than 32 characters.
- **Design improvement**: The compatibility guard is centralized in
  `packages/shared/alembic_compat.py`; migrations do not rewrite history.
- **Process improvement**: Migration startup commands must stop immediately on
  nonzero exit before starting API processes.

### 5. Knowledge Capture

- [x] Updated `.trellis/spec/backend/database-guidelines.md`.
- [x] Added `tests/shared/test_alembic_compat.py`.
- [x] Verified the real PostgreSQL database upgraded from `0009` to `0015`,
  version capacity is 128, and `research_evidence_backfills` exists.
