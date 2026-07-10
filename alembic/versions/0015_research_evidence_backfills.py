"""Add resumable A-share research evidence backfill state."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0015_research_evidence_backfills"
down_revision = "0014_instrument_universe_sync"
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
    op.add_column(
        "task_runs",
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
    )
    uuid_type = _uuid_type()
    op.create_table(
        "research_evidence_backfills",
        sa.Column("id", uuid_type, primary_key=True, server_default=_uuid_default()),
        sa.Column("task_run_id", uuid_type, nullable=True),
        sa.Column("parent_run_id", uuid_type, nullable=True),
        sa.Column("market", sa.String(32), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("run_kind", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("universe_sync_id", uuid_type, nullable=True),
        sa.Column("universe_as_of", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence_kinds_json", _json_type(), nullable=False),
        sa.Column("scope_symbols_json", _json_type(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("batch_size", sa.Integer(), nullable=False),
        sa.Column("cohort_size", sa.Integer(), nullable=True),
        sa.Column("shard_index", sa.Integer(), nullable=True),
        sa.Column("shard_count", sa.Integer(), nullable=True),
        sa.Column("phase", sa.String(32), nullable=False),
        sa.Column("cursor", sa.Integer(), nullable=False),
        sa.Column("phase_total", sa.Integer(), nullable=False),
        sa.Column("processed_count", sa.Integer(), nullable=False),
        sa.Column("counters_json", _json_type(), nullable=False),
        sa.Column("retry_json", _json_type(), nullable=False),
        sa.Column("diagnostics_json", _json_type(), nullable=False),
        sa.Column("cancel_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["task_run_id"], ["task_runs.id"]),
        sa.ForeignKeyConstraint(["parent_run_id"], ["research_evidence_backfills.id"]),
        sa.ForeignKeyConstraint(["universe_sync_id"], ["instrument_universe_syncs.id"]),
        sa.UniqueConstraint("task_run_id", name="uq_research_evidence_backfills_task_run"),
    )


def downgrade():
    op.drop_table("research_evidence_backfills")
    op.drop_column("task_runs", "heartbeat_at")
