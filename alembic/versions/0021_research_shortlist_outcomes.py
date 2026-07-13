"""Add terminal research shortlist candidate outcomes."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0021_research_shortlist_outcomes"
down_revision = "0020_research_shortlists"
branch_labels = None
depends_on = None


def _is_postgresql():
    bind = op.get_bind()
    return bind is not None and bind.dialect.name == "postgresql"


def _uuid_type():
    if _is_postgresql():
        return postgresql.UUID(as_uuid=True)
    return sa.String(36)


def _uuid_default():
    if _is_postgresql():
        return sa.text("gen_random_uuid()")
    return None


def _json_type():
    if _is_postgresql():
        return postgresql.JSONB()
    return sa.JSON()


def upgrade():
    uuid_type = _uuid_type()
    op.create_table(
        "research_candidate_outcomes",
        sa.Column("id", uuid_type, primary_key=True, server_default=_uuid_default()),
        sa.Column(
            "candidate_id",
            uuid_type,
            sa.ForeignKey("research_shortlist_candidates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("horizon_sessions", sa.Integer(), nullable=False),
        sa.Column("methodology_version", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("evaluation_as_of", sa.Date(), nullable=False),
        sa.Column("available_forward_bars", sa.Integer(), nullable=False),
        sa.Column(
            "evaluation_task_run_id",
            uuid_type,
            sa.ForeignKey("task_runs.id"),
            nullable=True,
        ),
        sa.Column("maturity_trade_date", sa.Date(), nullable=False),
        sa.Column("exit_close", sa.Numeric(20, 6), nullable=True),
        sa.Column("minimum_forward_low", sa.Numeric(20, 6), nullable=True),
        sa.Column("minimum_forward_low_trade_date", sa.Date(), nullable=True),
        sa.Column("return_ratio", sa.Numeric(20, 10), nullable=True),
        sa.Column("drawdown_ratio", sa.Numeric(20, 10), nullable=True),
        sa.Column("exit_provider", sa.String(64), nullable=True),
        sa.Column("exit_source", sa.String(128), nullable=True),
        sa.Column("exit_adjustment", sa.String(32), nullable=True),
        sa.Column("exit_source_priority", sa.Integer(), nullable=True),
        sa.Column("exit_ingested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("minimum_low_provider", sa.String(64), nullable=True),
        sa.Column("minimum_low_source", sa.String(128), nullable=True),
        sa.Column("minimum_low_adjustment", sa.String(32), nullable=True),
        sa.Column("minimum_low_source_priority", sa.Integer(), nullable=True),
        sa.Column("minimum_low_ingested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("benchmark_code", sa.String(64), nullable=False),
        sa.Column(
            "benchmark_instrument_id",
            uuid_type,
            sa.ForeignKey("instruments.id"),
            nullable=True,
        ),
        sa.Column("benchmark_status", sa.String(32), nullable=False),
        sa.Column("benchmark_entry_trade_date", sa.Date(), nullable=True),
        sa.Column("benchmark_entry_close", sa.Numeric(20, 6), nullable=True),
        sa.Column("benchmark_entry_provider", sa.String(64), nullable=True),
        sa.Column("benchmark_entry_source", sa.String(128), nullable=True),
        sa.Column("benchmark_entry_adjustment", sa.String(32), nullable=True),
        sa.Column("benchmark_entry_source_priority", sa.Integer(), nullable=True),
        sa.Column(
            "benchmark_entry_ingested_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("benchmark_exit_trade_date", sa.Date(), nullable=True),
        sa.Column("benchmark_exit_close", sa.Numeric(20, 6), nullable=True),
        sa.Column("benchmark_exit_provider", sa.String(64), nullable=True),
        sa.Column("benchmark_exit_source", sa.String(128), nullable=True),
        sa.Column("benchmark_exit_adjustment", sa.String(32), nullable=True),
        sa.Column("benchmark_exit_source_priority", sa.Integer(), nullable=True),
        sa.Column(
            "benchmark_exit_ingested_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("benchmark_return_ratio", sa.Numeric(20, 10), nullable=True),
        sa.Column("excess_return_ratio", sa.Numeric(20, 10), nullable=True),
        sa.Column("diagnostics_json", _json_type(), nullable=False),
        sa.Column("benchmark_diagnostics_json", _json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("benchmark_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "candidate_id",
            "horizon_sessions",
            name="uq_research_candidate_outcomes_horizon",
        ),
        sa.CheckConstraint(
            "horizon_sessions IN (5, 20, 60)",
            name="ck_research_candidate_outcomes_horizon_sessions",
        ),
        sa.CheckConstraint(
            "status IN ('evaluated', 'blocked')",
            name="ck_research_candidate_outcomes_status",
        ),
        sa.CheckConstraint(
            "benchmark_status IN ('pending', 'evaluated', 'blocked', 'not_applicable')",
            name="ck_research_candidate_outcomes_benchmark_status",
        ),
        sa.CheckConstraint(
            "available_forward_bars >= horizon_sessions",
            name="ck_research_candidate_outcomes_mature",
        ),
        sa.CheckConstraint(
            "evaluation_as_of >= maturity_trade_date",
            name="ck_research_candidate_outcomes_evaluation_order",
        ),
        sa.CheckConstraint(
            "(status = 'evaluated' AND exit_close IS NOT NULL "
            "AND minimum_forward_low IS NOT NULL "
            "AND minimum_forward_low_trade_date IS NOT NULL "
            "AND return_ratio IS NOT NULL AND drawdown_ratio IS NOT NULL "
            "AND exit_provider IS NOT NULL AND exit_source IS NOT NULL "
            "AND exit_adjustment IS NOT NULL AND exit_source_priority IS NOT NULL "
            "AND exit_ingested_at IS NOT NULL "
            "AND minimum_low_provider IS NOT NULL "
            "AND minimum_low_source IS NOT NULL "
            "AND minimum_low_adjustment IS NOT NULL "
            "AND minimum_low_source_priority IS NOT NULL "
            "AND minimum_low_ingested_at IS NOT NULL "
            "AND benchmark_status != 'not_applicable') OR "
            "(status = 'blocked' AND exit_close IS NULL "
            "AND minimum_forward_low IS NULL "
            "AND minimum_forward_low_trade_date IS NULL "
            "AND return_ratio IS NULL AND drawdown_ratio IS NULL "
            "AND exit_provider IS NULL AND exit_source IS NULL "
            "AND exit_adjustment IS NULL AND exit_source_priority IS NULL "
            "AND exit_ingested_at IS NULL "
            "AND minimum_low_provider IS NULL "
            "AND minimum_low_source IS NULL "
            "AND minimum_low_adjustment IS NULL "
            "AND minimum_low_source_priority IS NULL "
            "AND minimum_low_ingested_at IS NULL "
            "AND benchmark_status = 'not_applicable')",
            name="ck_research_candidate_outcomes_candidate_terminal_values",
        ),
        sa.CheckConstraint(
            "(benchmark_status = 'evaluated' "
            "AND benchmark_instrument_id IS NOT NULL "
            "AND benchmark_entry_trade_date IS NOT NULL "
            "AND benchmark_entry_close IS NOT NULL "
            "AND benchmark_entry_provider IS NOT NULL "
            "AND benchmark_entry_source IS NOT NULL "
            "AND benchmark_entry_adjustment IS NOT NULL "
            "AND benchmark_entry_source_priority IS NOT NULL "
            "AND benchmark_entry_ingested_at IS NOT NULL "
            "AND benchmark_exit_trade_date IS NOT NULL "
            "AND benchmark_exit_close IS NOT NULL "
            "AND benchmark_exit_provider IS NOT NULL "
            "AND benchmark_exit_source IS NOT NULL "
            "AND benchmark_exit_adjustment IS NOT NULL "
            "AND benchmark_exit_source_priority IS NOT NULL "
            "AND benchmark_exit_ingested_at IS NOT NULL "
            "AND benchmark_return_ratio IS NOT NULL "
            "AND excess_return_ratio IS NOT NULL "
            "AND benchmark_completed_at IS NOT NULL) OR "
            "(benchmark_status = 'blocked' "
            "AND benchmark_instrument_id IS NOT NULL "
            "AND benchmark_entry_trade_date IS NULL "
            "AND benchmark_entry_close IS NULL "
            "AND benchmark_entry_provider IS NULL "
            "AND benchmark_entry_source IS NULL "
            "AND benchmark_entry_adjustment IS NULL "
            "AND benchmark_entry_source_priority IS NULL "
            "AND benchmark_entry_ingested_at IS NULL "
            "AND benchmark_exit_trade_date IS NULL "
            "AND benchmark_exit_close IS NULL "
            "AND benchmark_exit_provider IS NULL "
            "AND benchmark_exit_source IS NULL "
            "AND benchmark_exit_adjustment IS NULL "
            "AND benchmark_exit_source_priority IS NULL "
            "AND benchmark_exit_ingested_at IS NULL "
            "AND benchmark_return_ratio IS NULL "
            "AND excess_return_ratio IS NULL "
            "AND benchmark_completed_at IS NOT NULL) OR "
            "(benchmark_status = 'pending' "
            "AND benchmark_entry_trade_date IS NULL "
            "AND benchmark_entry_close IS NULL "
            "AND benchmark_entry_provider IS NULL "
            "AND benchmark_entry_source IS NULL "
            "AND benchmark_entry_adjustment IS NULL "
            "AND benchmark_entry_source_priority IS NULL "
            "AND benchmark_entry_ingested_at IS NULL "
            "AND benchmark_exit_trade_date IS NULL "
            "AND benchmark_exit_close IS NULL "
            "AND benchmark_exit_provider IS NULL "
            "AND benchmark_exit_source IS NULL "
            "AND benchmark_exit_adjustment IS NULL "
            "AND benchmark_exit_source_priority IS NULL "
            "AND benchmark_exit_ingested_at IS NULL "
            "AND benchmark_return_ratio IS NULL "
            "AND excess_return_ratio IS NULL "
            "AND benchmark_completed_at IS NULL) OR "
            "(benchmark_status = 'not_applicable' "
            "AND benchmark_instrument_id IS NULL "
            "AND benchmark_entry_trade_date IS NULL "
            "AND benchmark_entry_close IS NULL "
            "AND benchmark_entry_provider IS NULL "
            "AND benchmark_entry_source IS NULL "
            "AND benchmark_entry_adjustment IS NULL "
            "AND benchmark_entry_source_priority IS NULL "
            "AND benchmark_entry_ingested_at IS NULL "
            "AND benchmark_exit_trade_date IS NULL "
            "AND benchmark_exit_close IS NULL "
            "AND benchmark_exit_provider IS NULL "
            "AND benchmark_exit_source IS NULL "
            "AND benchmark_exit_adjustment IS NULL "
            "AND benchmark_exit_source_priority IS NULL "
            "AND benchmark_exit_ingested_at IS NULL "
            "AND benchmark_return_ratio IS NULL "
            "AND excess_return_ratio IS NULL "
            "AND benchmark_completed_at IS NULL)",
            name="ck_research_candidate_outcomes_benchmark_terminal_values",
        ),
    )
    op.create_index(
        "ix_research_candidate_outcomes_candidate_id",
        "research_candidate_outcomes",
        ["candidate_id"],
    )


def downgrade():
    op.drop_index(
        "ix_research_candidate_outcomes_candidate_id",
        table_name="research_candidate_outcomes",
    )
    op.drop_table("research_candidate_outcomes")
