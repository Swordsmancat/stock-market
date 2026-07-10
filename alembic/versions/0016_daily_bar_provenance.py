"""Add canonical daily-bar provenance and backfill source policy."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0016_daily_bar_provenance"
down_revision = "0015_research_evidence_backfills"
branch_labels = None
depends_on = None


def _is_postgresql():
    bind = op.get_bind()
    return bind is not None and bind.dialect.name == "postgresql"


def _json_type():
    if _is_postgresql():
        return postgresql.JSONB()
    return sa.JSON()


def _empty_json_default():
    if _is_postgresql():
        return sa.text("'{}'::jsonb")
    return sa.text("'{}'")


def upgrade():
    op.add_column(
        "bars_1d",
        sa.Column(
            "provider",
            sa.String(64),
            nullable=False,
            server_default="legacy_unknown",
        ),
    )
    op.add_column(
        "bars_1d",
        sa.Column(
            "source",
            sa.String(128),
            nullable=False,
            server_default="legacy_unknown",
        ),
    )
    op.add_column(
        "bars_1d",
        sa.Column(
            "adjustment",
            sa.String(32),
            nullable=False,
            server_default="legacy_unknown",
        ),
    )
    op.add_column(
        "bars_1d",
        sa.Column("source_priority", sa.Integer(), nullable=False, server_default="99"),
    )
    op.add_column(
        "bars_1d",
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.add_column(
        "research_evidence_backfills",
        sa.Column(
            "daily_bar_policy",
            sa.String(32),
            nullable=False,
            server_default="strict",
        ),
    )
    op.add_column(
        "research_evidence_backfills",
        sa.Column(
            "source_stats_json",
            _json_type(),
            nullable=False,
            server_default=_empty_json_default(),
        ),
    )


def downgrade():
    op.drop_column("research_evidence_backfills", "source_stats_json")
    op.drop_column("research_evidence_backfills", "daily_bar_policy")
    op.drop_column("bars_1d", "ingested_at")
    op.drop_column("bars_1d", "source_priority")
    op.drop_column("bars_1d", "adjustment")
    op.drop_column("bars_1d", "source")
    op.drop_column("bars_1d", "provider")
