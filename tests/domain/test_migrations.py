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
    spec = importlib.util.spec_from_file_location(
        "fundamentals_watchlists_migration", migration_path
    )
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


def load_market_daily_evidence_migration():
    migration_path = Path("alembic/versions/0013_market_daily_evidence_events.py")
    spec = importlib.util.spec_from_file_location("market_daily_evidence_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_instrument_universe_migration():
    migration_path = Path("alembic/versions/0014_instrument_universe_sync.py")
    spec = importlib.util.spec_from_file_location("instrument_universe_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_research_evidence_backfill_migration():
    migration_path = Path("alembic/versions/0015_research_evidence_backfills.py")
    spec = importlib.util.spec_from_file_location(
        "research_evidence_backfill_migration",
        migration_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_daily_bar_provenance_migration():
    migration_path = Path("alembic/versions/0016_daily_bar_provenance.py")
    spec = importlib.util.spec_from_file_location("daily_bar_provenance_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_official_disclosures_migration():
    migration_path = Path("alembic/versions/0017_official_disclosures.py")
    spec = importlib.util.spec_from_file_location("official_disclosures_migration", migration_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_official_disclosure_documents_migration():
    migration_path = Path("alembic/versions/0018_official_disclosure_documents.py")
    spec = importlib.util.spec_from_file_location(
        "official_disclosure_documents_migration",
        migration_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_official_disclosures_migration_creates_metadata_table_and_identity_constraint():
    migration = load_official_disclosures_migration()
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        run_migration(migration, connection)
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        unique_constraints = inspector.get_unique_constraints("official_disclosures")

    assert "official_disclosures" in tables
    assert any(
        constraint["name"] == "uq_official_disclosures_source_document"
        and set(constraint["column_names"]) == {"source", "source_document_id"}
        for constraint in unique_constraints
    )


def test_official_disclosure_documents_migration_creates_versions_and_sections():
    metadata_migration = load_official_disclosures_migration()
    document_migration = load_official_disclosure_documents_migration()
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        run_migration(metadata_migration, connection)
        run_migration(document_migration, connection)
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        document_constraints = inspector.get_unique_constraints("official_disclosure_documents")
        section_constraints = inspector.get_unique_constraints("official_disclosure_sections")

    assert {"official_disclosure_documents", "official_disclosure_sections"}.issubset(tables)
    assert any(
        constraint["name"] == "uq_official_disclosure_documents_version"
        for constraint in document_constraints
    )
    assert any(
        constraint["name"] == "uq_official_disclosure_sections_index"
        for constraint in section_constraints
    )


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
        columns = {
            column["name"] for column in inspector.get_columns("intraday_minute_cache_entries")
        }

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


def test_market_daily_evidence_migration_creates_persisted_event_table():
    migration = load_market_daily_evidence_migration()
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        run_migration(migration, connection)

        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        columns = {
            column["name"] for column in inspector.get_columns("market_daily_evidence_events")
        }
        unique_constraints = {
            constraint["name"]
            for constraint in inspector.get_unique_constraints("market_daily_evidence_events")
        }

    assert "market_daily_evidence_events" in tables
    assert {
        "event_type",
        "identity",
        "identity_name",
        "market",
        "trade_date",
        "provider",
        "source",
        "as_of",
        "status",
        "is_citable",
        "payload_json",
        "availability_json",
        "provider_capabilities_json",
        "diagnostics_json",
        "imported_at",
        "updated_at",
    }.issubset(columns)
    assert "uq_market_daily_evidence_event_identity" in unique_constraints


def test_instrument_universe_migration_adds_provenance_and_sync_history():
    initial_migration = load_initial_migration()
    migration = load_instrument_universe_migration()
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        run_migration(initial_migration, connection)
        run_migration(migration, connection)

        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        instrument_columns = {column["name"] for column in inspector.get_columns("instruments")}
        sync_columns = {
            column["name"] for column in inspector.get_columns("instrument_universe_syncs")
        }

    assert "instrument_universe_syncs" in tables
    assert {"universe_provider", "universe_synced_at"}.issubset(instrument_columns)
    assert {
        "market",
        "provider",
        "source",
        "as_of",
        "status",
        "total_count",
        "inserted_count",
        "updated_count",
        "unchanged_count",
        "reactivated_count",
        "deactivated_count",
        "skipped_count",
        "availability_json",
        "diagnostics_json",
        "created_at",
    }.issubset(sync_columns)


def test_research_evidence_backfill_migration_adds_run_state_and_task_heartbeat():
    initial_migration = load_initial_migration()
    task_runs_migration = load_task_runs_migration()
    universe_migration = load_instrument_universe_migration()
    migration = load_research_evidence_backfill_migration()
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        run_migration(initial_migration, connection)
        run_migration(task_runs_migration, connection)
        run_migration(universe_migration, connection)
        run_migration(migration, connection)

        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        task_run_columns = {column["name"] for column in inspector.get_columns("task_runs")}
        backfill_columns = {
            column["name"] for column in inspector.get_columns("research_evidence_backfills")
        }

    assert "research_evidence_backfills" in tables
    assert "heartbeat_at" in task_run_columns
    assert {
        "task_run_id",
        "parent_run_id",
        "market",
        "provider",
        "run_kind",
        "status",
        "universe_sync_id",
        "universe_as_of",
        "evidence_kinds_json",
        "scope_symbols_json",
        "start_date",
        "end_date",
        "batch_size",
        "cohort_size",
        "shard_index",
        "shard_count",
        "phase",
        "cursor",
        "phase_total",
        "processed_count",
        "counters_json",
        "retry_json",
        "diagnostics_json",
        "cancel_requested_at",
        "heartbeat_at",
        "created_at",
        "updated_at",
        "finished_at",
    }.issubset(backfill_columns)


def test_daily_bar_provenance_migration_adds_source_and_policy_fields():
    initial_migration = load_initial_migration()
    task_runs_migration = load_task_runs_migration()
    universe_migration = load_instrument_universe_migration()
    backfill_migration = load_research_evidence_backfill_migration()
    migration = load_daily_bar_provenance_migration()
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        run_migration(initial_migration, connection)
        run_migration(task_runs_migration, connection)
        run_migration(universe_migration, connection)
        run_migration(backfill_migration, connection)
        run_migration(migration, connection)

        inspector = inspect(connection)
        bar_columns = {column["name"] for column in inspector.get_columns("bars_1d")}
        backfill_columns = {
            column["name"] for column in inspector.get_columns("research_evidence_backfills")
        }

    assert {"provider", "source", "adjustment", "source_priority", "ingested_at"}.issubset(
        bar_columns
    )
    assert {"daily_bar_policy", "source_stats_json"}.issubset(backfill_columns)
