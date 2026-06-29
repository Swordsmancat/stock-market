import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect


def load_initial_migration():
    migration_path = Path("alembic/versions/0001_core_schema.py")
    spec = importlib.util.spec_from_file_location("initial_schema_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_initial_migration_creates_current_core_tables():
    migration = load_initial_migration()
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        original_op = migration.op
        migration.op = Operations(context)
        try:
            migration.upgrade()
        finally:
            migration.op = original_op

        tables = set(inspect(connection).get_table_names())

    assert {
        "markets",
        "exchanges",
        "instruments",
        "data_sources",
        "bars_1d",
        "bars_1m",
        "technical_indicators",
    }.issubset(tables)
