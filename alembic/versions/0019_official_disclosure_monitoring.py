"""Add durable official disclosure monitoring state."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0019_official_disclosure_monitoring"
down_revision = "0018_official_disclosure_documents"
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


def upgrade():
    uuid_type = _uuid_type()
    op.create_table(
        "official_disclosure_monitor_states",
        sa.Column("id", uuid_type, primary_key=True, server_default=_uuid_default()),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("cursor_published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cursor_source_document_id", sa.String(128), nullable=True),
        sa.Column("last_attempted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.String(128), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("last_new_disclosure_count", sa.Integer(), nullable=False),
        sa.Column(
            "last_task_run_id",
            uuid_type,
            sa.ForeignKey("task_runs.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "source",
            "symbol",
            name="uq_official_disclosure_monitor_source_symbol",
        ),
    )
    op.create_index(
        "ix_official_disclosure_monitor_states_symbol",
        "official_disclosure_monitor_states",
        ["symbol"],
    )


def downgrade():
    op.drop_index(
        "ix_official_disclosure_monitor_states_symbol",
        table_name="official_disclosure_monitor_states",
    )
    op.drop_table("official_disclosure_monitor_states")
