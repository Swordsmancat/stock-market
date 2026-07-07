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


def load_intraday_minute_cache_migration():
    migration_path = Path("alembic/versions/0010_intraday_minute_cache_entries.py")
    spec = importlib.util.spec_from_file_location("intraday_minute_cache_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_research_source_notes_migration():
    migration_path = Path("alembic/versions/0011_research_source_notes.py")
    spec = importlib.util.spec_from_file_location("research_source_notes_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_research_briefs_migration():
    migration_path = Path("alembic/versions/0012_research_briefs.py")
    spec = importlib.util.spec_from_file_location("research_briefs_migration", migration_path)
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


def test_intraday_minute_cache_migration_creates_cache_metadata_table():
    initial_migration = load_initial_migration()
    intraday_cache_migration = load_intraday_minute_cache_migration()
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        run_migration(initial_migration, connection)
        run_migration(intraday_cache_migration, connection)

        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        columns = {column["name"] for column in inspector.get_columns("intraday_minute_cache_entries")}

    assert "intraday_minute_cache_entries" in tables
    assert {
        "instrument_id",
        "provider",
        "symbol",
        "trade_date",
        "timeframe",
        "row_count",
        "first_ts",
        "last_ts",
        "fetched_at",
        "cached_at",
    }.issubset(columns)


def test_research_source_notes_migration_creates_notebook_table():
    initial_migration = load_initial_migration()
    research_source_notes_migration = load_research_source_notes_migration()
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        run_migration(initial_migration, connection)
        run_migration(research_source_notes_migration, connection)

        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        columns = {column["name"] for column in inspector.get_columns("research_source_notes")}

    assert "research_source_notes" in tables
    assert {
        "title",
        "source_url",
        "source_name",
        "source_type",
        "symbols_json",
        "tags_json",
        "excerpt",
        "note",
        "ai_follow_up",
        "review_status",
        "is_citable",
        "metadata_json",
    }.issubset(columns)


def test_research_briefs_migration_creates_brief_inbox_table():
    initial_migration = load_initial_migration()
    research_briefs_migration = load_research_briefs_migration()
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        run_migration(initial_migration, connection)
        run_migration(research_briefs_migration, connection)

        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        columns = {column["name"] for column in inspector.get_columns("research_briefs")}

    assert "research_briefs" in tables
    assert {
        "title",
        "brief_type",
        "scope_json",
        "content_markdown",
        "citations_json",
        "source_summary_json",
        "diagnostics_json",
        "model_json",
        "safety_json",
        "created_at",
    }.issubset(columns)
