# Bug Analysis: Fresh PostgreSQL recreated Alembic's short version column

## 1. Root Cause Category

- **Category**: D - Test Coverage Gap and E - Implicit Assumption.
- **Specific cause**: the compatibility guard widened an existing
  `alembic_version` table but assumed a fresh database needed no action. Alembic
  subsequently created its default `VARCHAR(32)` table and failed at revision
  `0010_intraday_minute_cache_entries`.

## 2. Why the earlier fix was incomplete

1. The regression mocked only `has_table=True`, so it proved legacy upgrades
   but not first installation.
2. Normal development validation ran against an already-stamped database.
3. The first real empty PostgreSQL path was the isolated acceptance volume.

## 3. Prevention Mechanisms

| Priority | Mechanism | Specific action | Status |
|---|---|---|---|
| P0 | Runtime guard | Pre-create a 128-character version table on fresh PostgreSQL | DONE |
| P0 | Regression | Assert fresh-table creation and legacy widening separately | DONE |
| P1 | Integration | Start an empty isolated PostgreSQL stack through Alembic head | DONE |
| P1 | Documentation | Update backend database migration guidance | DONE |

## 4. Systematic Expansion

- **Similar issue**: any bootstrap guard that only inspects existing metadata
  may miss framework-created defaults on first install.
- **Design improvement**: compatibility ownership begins before framework
  initialization, not only after old state exists.
- **Process improvement**: validate additive migrations against both a current
  database and a genuinely empty PostgreSQL database.

## 5. Knowledge Capture

- [x] Added fresh PostgreSQL regression coverage.
- [x] Updated `.trellis/spec/backend/database-guidelines.md`.
- [x] Recorded successful empty-stack migration to revision `0016`.
