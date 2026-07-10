# Database Guidelines

> SQLAlchemy, migration, and test-database patterns currently used by the backend.

---

## Overview

The backend uses SQLAlchemy ORM with a shared declarative base and session factory. Runtime database configuration comes from pydantic settings, FastAPI routes receive sessions through dependency injection, Celery tasks open `SessionLocal()` manually, and tests usually create an isolated in-memory SQLite database with `StaticPool`.

Concrete examples:

- `packages/shared/database.py` defines `Base`, `engine`, `SessionLocal`, and the FastAPI `get_session()` generator.
- `packages/domain/models.py` defines ORM models using `Mapped[...]`, `mapped_column()`, relationships, UUID primary keys, JSON/JSONB variants, and explicit constraints.
- `apps/api/routers/market_data.py`, `apps/api/routers/fundamentals.py`, and `apps/api/routers/task_runs.py` receive `Session = Depends(get_session)`.
- `apps/worker/tasks/ingestion.py`, `apps/worker/tasks/reports.py`, and `apps/worker/tasks/alerts.py` create sessions with `SessionLocal()` and close them in `finally`.
- `alembic/env.py`, `alembic/versions/0001_core_schema.py`, and `alembic/versions/0005_fundamentals_watchlists.py` show current migration wiring.
- `tests/api/test_ingestion_api.py`, `tests/services/test_report_service.py`, and `tests/scripts/test_task_run_health.py` show SQLite/`StaticPool` test database setup.

---

## Session Ownership

`packages/shared/database.py` is the database entry point:

- `Base` subclasses `DeclarativeBase`.
- `engine = create_engine(settings.database_url, pool_pre_ping=True)`.
- `SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)`.
- `get_session()` yields one session and always closes it.

Follow these existing ownership boundaries:

- FastAPI routers depend on `get_session()` and pass the session into services. Examples: `apps/api/routers/fundamentals.py`, `apps/api/routers/ingestion.py`, `apps/api/routers/task_runs.py`.
- Services accept a `Session` when they read or write database state. Examples: `packages/services/ingestion.py`, `packages/services/watchlists.py`, `packages/services/task_runs.py`.
- Celery tasks create their own `SessionLocal()` session because they run outside FastAPI dependency injection. Examples: `apps/worker/tasks/ingestion.py`, `apps/worker/tasks/reports.py`, `apps/worker/tasks/alerts.py`.
- Tests override the session boundary rather than using the real database. Examples: `tests/api/test_ingestion_api.py`, `tests/worker/test_tasks.py`, `tests/helpers/celery_sync.py`.

---

## ORM Model Patterns

`packages/domain/models.py` is the current source of truth for database models.

Observed model patterns:

- UUID primary keys use the local `uuid_pk()` helper for most entity tables, for example `Market`, `Instrument`, `Watchlist`, `GeneratedReport`, and `TaskRun`.
- Time-series bars use composite primary keys instead of surrogate IDs: `DailyBar` uses `(instrument_id, trade_date)` and `MinuteBar` uses `(instrument_id, ts)`.
- JSON fields use `JSON().with_variant(JSONB, "postgresql")`, for example `TechnicalIndicator.params`, `WatchlistItem.alert_rules`, `GeneratedReport.citations`, and `TaskRun.input_json`.
- Timestamps are timezone-aware with `DateTime(timezone=True)` and commonly default to `datetime.now(timezone.utc)`.
- Uniqueness rules are named when they represent domain identity, for example `uq_instruments_market_symbol`, `uq_fundamental_snapshots_symbol_as_of`, `uq_watchlist_items_identity`, and `uq_portfolio_positions_identity`.
- Relationships are declared where services use object navigation, for example `Watchlist.items`, `WatchlistItem.watchlist`, `Portfolio.positions`, and `SentimentSignal.article`.

When changing models, keep `packages/domain/models.py` aligned with Alembic versions under `alembic/versions/` and with SQLite-backed tests that call `Base.metadata.create_all()`.

---

## Query and Write Patterns

The current services use SQLAlchemy ORM query methods directly. They favor explicit filters and small helper functions over a repository abstraction.

Examples:

- `packages/services/market_data.py` joins `DailyBar`, `Instrument`, and `Market` to read database bars, then falls back to provider data when no database rows exist.
- `packages/services/ingestion.py` uses `_get_or_create_market()` and `_get_or_create_instrument()` helpers, `session.flush()` to obtain IDs, `session.get(DailyBar, (instrument.id, trade_date))` for composite-key upserts, and a final `session.commit()`.
- `packages/services/watchlists.py` queries the default watchlist, seeds default items when empty, upserts active items, and soft-removes items by setting `is_active = False` before committing.
- `packages/services/task_runs.py` uses `session.get(TaskRun, uuid)`, `query.order_by(...).limit(...).all()`, and explicit `commit()` calls in `start_task_run()`, `finish_task_run()`, and `fail_task_run()`.
- `packages/services/fundamentals.py` rolls back the session after `SQLAlchemyError` when database lookup fails and then falls back to fixture/provider payloads.

Current write behavior is service-owned. If a service writes data, it usually commits before returning a serialized payload. Existing examples include:

- `packages/services/ingestion.py` committing after writing a market snapshot.
- `packages/services/fundamentals.py` committing inside `upsert_fundamental_snapshot()`.
- `packages/services/watchlists.py` committing inside `upsert_watchlist_item()` and `remove_watchlist_item()`.
- `packages/services/task_runs.py` committing lifecycle transitions for running, succeeded, failed, stale, and retry task runs.

---

## Migrations

Alembic is configured under `alembic/`.

Observed migration patterns:

- `alembic/env.py` imports `packages.domain.models` so SQLAlchemy metadata is populated, sets `sqlalchemy.url` from `settings.database_url`, and uses `Base.metadata` as `target_metadata`.
- Revision files live in `alembic/versions/` and use numbered names such as `0001_core_schema.py`, `0005_fundamentals_watchlists.py`, `0006_task_run_celery_id.py`, and `0008_alert_triggers_report_task_run.py`.
- Revisions define `revision`, `down_revision`, `upgrade()`, and `downgrade()`.
- Earlier migrations handle PostgreSQL-vs-SQLite differences explicitly with helpers such as `_is_postgresql()`, `_uuid_type()`, `_uuid_default()`, and `_json_type()` in `alembic/versions/0001_core_schema.py` and `alembic/versions/0005_fundamentals_watchlists.py`.
- PostgreSQL-specific setup exists in `alembic/versions/0001_core_schema.py`: `CREATE EXTENSION IF NOT EXISTS timescaledb`, `CREATE EXTENSION IF NOT EXISTS pgcrypto`, and `create_hypertable('bars_1m', 'ts', if_not_exists => TRUE)`.
- Small additive migrations can be direct, as in `alembic/versions/0006_task_run_celery_id.py` adding and dropping `task_runs.celery_task_id`.

Keep new database changes represented in both `packages/domain/models.py` and a new Alembic revision. Do not edit old applied revisions unless the user explicitly asks for a history rewrite.

---

## SQLite Test Database Pattern

Focused tests use in-memory SQLite rather than the configured PostgreSQL database.

Observed setup:

```python
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(engine)
session = sessionmaker(bind=engine)()
```

Examples:

- `tests/api/test_ingestion_api.py` creates an in-memory database, overrides `get_session`, and clears `app.dependency_overrides` in `finally`.
- `tests/services/test_report_service.py` imports `packages.domain.models` to register models, calls `Base.metadata.create_all(engine)`, and uses the session for service calls.
- `tests/services/test_watchlists_service.py` follows the same `StaticPool` pattern for watchlist persistence tests.
- `tests/scripts/test_task_run_health.py` uses `sqlite://`, `StaticPool`, a `sessionmaker(..., autoflush=False, autocommit=False)`, and drops metadata after the fixture.
- `tests/worker/test_tasks.py` monkeypatches worker `SessionLocal` to return the test session.

---

## Common Mistakes

- Do not create ad hoc SQLAlchemy engines inside routers or services. Use `packages/shared/database.py` at runtime and test-local engines inside tests.
- Do not let worker sessions leak. Existing worker tasks close sessions in `finally`.
- Do not bypass service-owned commits for existing write flows unless the surrounding service is redesigned. Current write services commit internally.
- Do not assume PostgreSQL-only types in migrations without a SQLite-compatible path; tests and some migrations already support SQLite.
- Do not add database-backed tests that touch the real `settings.database_url` when nearby tests use SQLite/`StaticPool`.

### Alembic revision identifier capacity

PostgreSQL enforces the declared length of `alembic_version.version_num`.
Alembic creates legacy version tables as `VARCHAR(32)`, while this repository
uses descriptive revision identifiers such as
`0010_intraday_minute_cache_entries` that exceed 32 characters. A lagging
database can therefore run a migration's DDL and then fail when Alembic writes
the new revision identifier; transactional DDL rolls the migration back and the
application starts against missing tables.

`packages/shared/alembic_compat.py` owns the compatibility guard.
`alembic/env.py` runs it in a dedicated transaction before configuring the
migration context. For an existing PostgreSQL `alembic_version` table it widens
`version_num` to `VARCHAR(128)` when needed. For a fresh PostgreSQL database it
pre-creates the same version table at `VARCHAR(128)` before Alembic can create
its default 32-character table. Non-PostgreSQL dialects remain unchanged.

Required checks:

- `tests/shared/test_alembic_compat.py` must assert the PostgreSQL widening SQL,
  fresh-database creation SQL, no-op behavior for current/SQLite schemas, and
  that every revision identifier fits the 128-character capacity.
- A fresh isolated PostgreSQL Compose start must migrate from an empty database
  through every descriptive revision identifier; testing only an already-
  stamped development database does not cover this boundary.
- When diagnosing an application that starts but reports missing new tables,
  run `alembic current` and inspect both the version-column length and actual
  table presence; `alembic heads` only reports repository state.
- Do not shorten or rewrite applied revision identifiers to work around this
  failure. Preserve history and fix the version-table compatibility boundary.
