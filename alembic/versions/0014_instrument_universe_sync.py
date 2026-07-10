"""Add A-share instrument universe provenance and sync history."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0014_instrument_universe_sync"
down_revision = "0013_market_daily_evidence_events"
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
    op.add_column("instruments", sa.Column("universe_provider", sa.String(64), nullable=True))
    op.add_column(
        "instruments",
        sa.Column("universe_synced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "instrument_universe_syncs",
        sa.Column("id", _uuid_type(), primary_key=True, server_default=_uuid_default()),
        sa.Column("market", sa.String(32), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("source", sa.String(512), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("inserted_count", sa.Integer(), nullable=False),
        sa.Column("updated_count", sa.Integer(), nullable=False),
        sa.Column("unchanged_count", sa.Integer(), nullable=False),
        sa.Column("reactivated_count", sa.Integer(), nullable=False),
        sa.Column("deactivated_count", sa.Integer(), nullable=False),
        sa.Column("skipped_count", sa.Integer(), nullable=False),
        sa.Column("availability_json", _json_type(), nullable=False),
        sa.Column("diagnostics_json", _json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("instrument_universe_syncs")
    op.drop_column("instruments", "universe_synced_at")
    op.drop_column("instruments", "universe_provider")
