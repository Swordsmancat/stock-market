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


def load_official_disclosure_monitoring_migration():
    migration_path = Path("alembic/versions/0019_official_disclosure_monitoring.py")
    spec = importlib.util.spec_from_file_location(
        "official_disclosure_monitoring_migration",
        migration_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_research_shortlists_migration():
    migration_path = Path("alembic/versions/0020_research_shortlists.py")
    spec = importlib.util.spec_from_file_location(
        "research_shortlists_migration",
        migration_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_research_shortlist_outcomes_migration():
    migration_path = Path("alembic/versions/0021_research_shortlist_outcomes.py")
    spec = importlib.util.spec_from_file_location(
        "research_shortlist_outcomes_migration",
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


def test_official_disclosure_monitoring_migration_creates_durable_symbol_state():
    migration = load_official_disclosure_monitoring_migration()
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        run_migration(migration, connection)
        inspector = inspect(connection)
        columns = {column["name"] for column in inspector.get_columns(
            "official_disclosure_monitor_states"
        )}
        constraints = inspector.get_unique_constraints(
            "official_disclosure_monitor_states"
        )

    assert {
        "cursor_published_at",
        "cursor_source_document_id",
        "last_success_at",
        "next_retry_at",
        "consecutive_failures",
        "last_new_disclosure_count",
    }.issubset(columns)
    assert any(
        constraint["name"] == "uq_official_disclosure_monitor_source_symbol"
        and set(constraint["column_names"]) == {"source", "symbol"}
        for constraint in constraints
    )

    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        original_op = migration.op
        migration.op = Operations(context)
        try:
            migration.downgrade()
        finally:
            migration.op = original_op
        assert "official_disclosure_monitor_states" not in inspect(connection).get_table_names()


def test_research_shortlists_migration_creates_immutable_run_and_candidate_tables():
    initial_migration = load_initial_migration()
    migration = load_research_shortlists_migration()
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        run_migration(initial_migration, connection)
        run_migration(migration, connection)
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        run_columns = {
            column["name"] for column in inspector.get_columns("research_shortlist_runs")
        }
        candidate_columns = {
            column["name"]
            for column in inspector.get_columns("research_shortlist_candidates")
        }
        run_constraints = inspector.get_unique_constraints("research_shortlist_runs")
        run_indexes = inspector.get_indexes("research_shortlist_runs")
        candidate_constraints = inspector.get_unique_constraints(
            "research_shortlist_candidates"
        )
        candidate_foreign_keys = inspector.get_foreign_keys(
            "research_shortlist_candidates"
        )

    assert {"research_shortlist_runs", "research_shortlist_candidates"}.issubset(tables)
    assert {
        "generation_key",
        "decision_date",
        "scoring_model",
        "coverage_json",
        "explanation_markdown",
        "safety_json",
    }.issubset(run_columns)
    assert {
        "run_id",
        "instrument_id",
        "rank",
        "total_score",
        "entry_trade_date",
        "entry_provider",
        "factor_scores_json",
        "invalidation_conditions_json",
        "safety_json",
    }.issubset(candidate_columns)
    assert any(
        constraint["name"] == "uq_research_shortlist_runs_generation_key"
        for constraint in run_constraints
    )
    assert any(
        index["name"] == "ix_research_shortlist_runs_latest"
        and index["column_names"]
        == ["market", "profile_id", "decision_date", "generated_at"]
        for index in run_indexes
    )
    assert {
        constraint["name"] for constraint in candidate_constraints
    } >= {
        "uq_research_shortlist_candidates_instrument",
        "uq_research_shortlist_candidates_rank",
    }
    assert any(
        foreign_key["referred_table"] == "research_shortlist_runs"
        and foreign_key.get("options", {}).get("ondelete") == "CASCADE"
        for foreign_key in candidate_foreign_keys
    )

    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        original_op = migration.op
        migration.op = Operations(context)
        try:
            migration.downgrade()
        finally:
            migration.op = original_op
        tables_after_downgrade = set(inspect(connection).get_table_names())

    assert "research_shortlist_candidates" not in tables_after_downgrade
    assert "research_shortlist_runs" not in tables_after_downgrade


def test_research_shortlist_outcomes_migration_creates_terminal_ledger():
    initial_migration = load_initial_migration()
    task_runs_migration = load_task_runs_migration()
    shortlists_migration = load_research_shortlists_migration()
    outcomes_migration = load_research_shortlist_outcomes_migration()
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as connection:
        run_migration(initial_migration, connection)
        run_migration(task_runs_migration, connection)
        run_migration(shortlists_migration, connection)
        run_migration(outcomes_migration, connection)
        inspector = inspect(connection)
        columns = {
            column["name"]: column
            for column in inspector.get_columns("research_candidate_outcomes")
        }
        unique_constraints = inspector.get_unique_constraints(
            "research_candidate_outcomes"
        )
        check_constraints = inspector.get_check_constraints(
            "research_candidate_outcomes"
        )
        foreign_keys = inspector.get_foreign_keys("research_candidate_outcomes")
        indexes = inspector.get_indexes("research_candidate_outcomes")

    assert {
        "candidate_id",
        "horizon_sessions",
        "methodology_version",
        "status",
        "evaluation_as_of",
        "available_forward_bars",
        "evaluation_task_run_id",
        "maturity_trade_date",
        "exit_close",
        "minimum_forward_low",
        "minimum_forward_low_trade_date",
        "return_ratio",
        "drawdown_ratio",
        "exit_provider",
        "exit_source",
        "exit_adjustment",
        "exit_source_priority",
        "exit_ingested_at",
        "minimum_low_provider",
        "minimum_low_source",
        "minimum_low_adjustment",
        "minimum_low_source_priority",
        "minimum_low_ingested_at",
        "benchmark_code",
        "benchmark_instrument_id",
        "benchmark_status",
        "benchmark_entry_trade_date",
        "benchmark_entry_close",
        "benchmark_entry_provider",
        "benchmark_entry_source",
        "benchmark_entry_adjustment",
        "benchmark_entry_source_priority",
        "benchmark_entry_ingested_at",
        "benchmark_exit_trade_date",
        "benchmark_exit_close",
        "benchmark_exit_provider",
        "benchmark_exit_source",
        "benchmark_exit_adjustment",
        "benchmark_exit_source_priority",
        "benchmark_exit_ingested_at",
        "benchmark_return_ratio",
        "excess_return_ratio",
        "diagnostics_json",
        "benchmark_diagnostics_json",
        "created_at",
        "evaluated_at",
        "benchmark_completed_at",
    }.issubset(columns)
    assert columns["maturity_trade_date"]["nullable"] is False
    assert columns["return_ratio"]["type"].precision == 20
    assert columns["return_ratio"]["type"].scale == 10
    assert columns["benchmark_return_ratio"]["nullable"] is True
    assert columns["excess_return_ratio"]["nullable"] is True
    assert any(
        constraint["name"] == "uq_research_candidate_outcomes_horizon"
        and set(constraint["column_names"]) == {"candidate_id", "horizon_sessions"}
        for constraint in unique_constraints
    )
    assert {constraint["name"] for constraint in check_constraints} >= {
        "ck_research_candidate_outcomes_horizon_sessions",
        "ck_research_candidate_outcomes_status",
        "ck_research_candidate_outcomes_benchmark_status",
        "ck_research_candidate_outcomes_mature",
        "ck_research_candidate_outcomes_evaluation_order",
        "ck_research_candidate_outcomes_candidate_terminal_values",
        "ck_research_candidate_outcomes_benchmark_terminal_values",
    }
    assert any(
        foreign_key["constrained_columns"] == ["candidate_id"]
        and foreign_key["referred_table"] == "research_shortlist_candidates"
        and foreign_key.get("options", {}).get("ondelete") == "CASCADE"
        for foreign_key in foreign_keys
    )
    assert any(
        foreign_key["constrained_columns"] == ["benchmark_instrument_id"]
        and foreign_key["referred_table"] == "instruments"
        for foreign_key in foreign_keys
    )
    assert any(
        foreign_key["constrained_columns"] == ["evaluation_task_run_id"]
        and foreign_key["referred_table"] == "task_runs"
        for foreign_key in foreign_keys
    )
    assert any(
        index["name"] == "ix_research_candidate_outcomes_candidate_id"
        and index["column_names"] == ["candidate_id"]
        for index in indexes
    )

    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        original_op = outcomes_migration.op
        outcomes_migration.op = Operations(context)
        try:
            outcomes_migration.downgrade()
        finally:
            outcomes_migration.op = original_op
        tables_after_downgrade = set(inspect(connection).get_table_names())

    assert "research_candidate_outcomes" not in tables_after_downgrade
    assert "research_shortlist_candidates" in tables_after_downgrade


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
