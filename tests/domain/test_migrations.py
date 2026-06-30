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


def load_news_migration():
    migration_path = Path("alembic/versions/0002_news_sentiment.py")
    spec = importlib.util.spec_from_file_location("news_sentiment_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_generated_reports_migration():
    migration_path = Path("alembic/versions/0003_generated_reports.py")
    spec = importlib.util.spec_from_file_location("generated_reports_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_task_runs_migration():
    migration_path = Path("alembic/versions/0004_task_runs.py")
    spec = importlib.util.spec_from_file_location("task_runs_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_fundamentals_watchlists_migration():
    migration_path = Path("alembic/versions/0005_fundamentals_watchlists.py")
    spec = importlib.util.spec_from_file_location("fundamentals_watchlists_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_migration(migration, connection):
    context = MigrationContext.configure(connection)
    original_op = migration.op
    migration.op = Operations(context)
    try:
        migration.upgrade()
    finally:
        migration.op = original_op


def test_initial_migration_creates_current_core_tables():
    migration = load_initial_migration()
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        run_migration(migration, connection)

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


def test_news_sentiment_migration_creates_news_tables():
    initial_migration = load_initial_migration()
    news_migration = load_news_migration()
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        run_migration(initial_migration, connection)
        run_migration(news_migration, connection)

        tables = set(inspect(connection).get_table_names())

    assert {"news_articles", "sentiment_signals"}.issubset(tables)


def test_generated_reports_migration_creates_report_table():
    initial_migration = load_initial_migration()
    news_migration = load_news_migration()
    generated_reports_migration = load_generated_reports_migration()
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        run_migration(initial_migration, connection)
        run_migration(news_migration, connection)
        run_migration(generated_reports_migration, connection)

        tables = set(inspect(connection).get_table_names())

    assert "generated_reports" in tables


def test_task_runs_migration_creates_task_runs_table():
    initial_migration = load_initial_migration()
    news_migration = load_news_migration()
    generated_reports_migration = load_generated_reports_migration()
    task_runs_migration = load_task_runs_migration()
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        run_migration(initial_migration, connection)
        run_migration(news_migration, connection)
        run_migration(generated_reports_migration, connection)
        run_migration(task_runs_migration, connection)

        tables = set(inspect(connection).get_table_names())

    assert "task_runs" in tables


def test_fundamentals_watchlists_migration_creates_persistent_analysis_tables():
    initial_migration = load_initial_migration()
    news_migration = load_news_migration()
    generated_reports_migration = load_generated_reports_migration()
    task_runs_migration = load_task_runs_migration()
    fundamentals_watchlists_migration = load_fundamentals_watchlists_migration()
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        run_migration(initial_migration, connection)
        run_migration(news_migration, connection)
        run_migration(generated_reports_migration, connection)
        run_migration(task_runs_migration, connection)
        run_migration(fundamentals_watchlists_migration, connection)

        tables = set(inspect(connection).get_table_names())

    assert {"fundamental_snapshots", "watchlists", "watchlist_items"}.issubset(tables)
