"""Add persisted daily research shortlist snapshots."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0020_research_shortlists"
down_revision = "0019_official_disclosure_monitoring"
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
    json_type = _json_type()
    op.create_table(
        "research_shortlist_runs",
        sa.Column("id", uuid_type, primary_key=True, server_default=_uuid_default()),
        sa.Column("generation_key", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("decision_date", sa.Date(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("market", sa.String(32), nullable=False),
        sa.Column("asset_type", sa.String(32), nullable=False),
        sa.Column("profile_id", sa.String(64), nullable=False),
        sa.Column("rule_set", sa.String(64), nullable=False),
        sa.Column("scoring_model", sa.String(64), nullable=False),
        sa.Column("locale", sa.String(8), nullable=False),
        sa.Column("shortlist_limit", sa.Integer(), nullable=False),
        sa.Column("default_criteria_json", json_type, nullable=False),
        sa.Column("effective_criteria_json", json_type, nullable=False),
        sa.Column("overrides_json", json_type, nullable=False),
        sa.Column("dimension_weights_json", json_type, nullable=False),
        sa.Column("candidate_scope_json", json_type, nullable=False),
        sa.Column("coverage_json", json_type, nullable=False),
        sa.Column("diagnostics_json", json_type, nullable=False),
        sa.Column("explanation_markdown", sa.Text(), nullable=False),
        sa.Column("model_json", json_type, nullable=False),
        sa.Column("citations_json", json_type, nullable=False),
        sa.Column("safety_json", json_type, nullable=False),
        sa.Column("research_signal_only", sa.Boolean(), nullable=False),
        sa.UniqueConstraint(
            "generation_key",
            name="uq_research_shortlist_runs_generation_key",
        ),
    )
    op.create_index(
        "ix_research_shortlist_runs_latest",
        "research_shortlist_runs",
        ["market", "profile_id", "decision_date", "generated_at"],
    )

    op.create_table(
        "research_shortlist_candidates",
        sa.Column("id", uuid_type, primary_key=True, server_default=_uuid_default()),
        sa.Column(
            "run_id",
            uuid_type,
            sa.ForeignKey("research_shortlist_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "instrument_id",
            uuid_type,
            sa.ForeignKey("instruments.id"),
            nullable=False,
        ),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("market", sa.String(32), nullable=False),
        sa.Column("asset_type", sa.String(32), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("total_score", sa.Numeric(8, 4), nullable=False),
        sa.Column("minimum_rule_buffer", sa.Numeric(8, 4), nullable=False),
        sa.Column("entry_trade_date", sa.Date(), nullable=False),
        sa.Column("entry_close", sa.Numeric(20, 6), nullable=False),
        sa.Column("entry_provider", sa.String(64), nullable=False),
        sa.Column("entry_source", sa.String(128), nullable=False),
        sa.Column("entry_adjustment", sa.String(32), nullable=False),
        sa.Column("entry_source_priority", sa.Integer(), nullable=False),
        sa.Column("entry_ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("factor_scores_json", json_type, nullable=False),
        sa.Column("supporting_factors_json", json_type, nullable=False),
        sa.Column("opposing_factors_json", json_type, nullable=False),
        sa.Column("data_gaps_json", json_type, nullable=False),
        sa.Column("invalidation_conditions_json", json_type, nullable=False),
        sa.Column("evidence_json", json_type, nullable=False),
        sa.Column("matched_rules_json", json_type, nullable=False),
        sa.Column("citations_json", json_type, nullable=False),
        sa.Column("safety_json", json_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "run_id",
            "instrument_id",
            name="uq_research_shortlist_candidates_instrument",
        ),
        sa.UniqueConstraint(
            "run_id",
            "rank",
            name="uq_research_shortlist_candidates_rank",
        ),
    )
    op.create_index(
        "ix_research_shortlist_candidates_run_id",
        "research_shortlist_candidates",
        ["run_id"],
    )


def downgrade():
    op.drop_index(
        "ix_research_shortlist_candidates_run_id",
        table_name="research_shortlist_candidates",
    )
    op.drop_table("research_shortlist_candidates")
    op.drop_index(
        "ix_research_shortlist_runs_latest",
        table_name="research_shortlist_runs",
    )
    op.drop_table("research_shortlist_runs")
