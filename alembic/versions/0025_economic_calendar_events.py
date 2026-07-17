"""Add persisted economic calendar events."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0025_economic_calendar_events"
down_revision = "0024_nullable_fundamental_metrics"
branch_labels = None
depends_on = None


def _postgresql():
    bind = op.get_bind()
    return bind is not None and bind.dialect.name == "postgresql"


def upgrade():
    uuid_type = postgresql.UUID(as_uuid=True) if _postgresql() else sa.String(36)
    uuid_default = sa.text("gen_random_uuid()") if _postgresql() else None
    json_type = postgresql.JSONB() if _postgresql() else sa.JSON()
    op.create_table(
        "economic_calendar_events",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("external_event_id", sa.String(128), nullable=False),
        sa.Column("indicator_id", sa.String(64), nullable=True),
        sa.Column("country", sa.String(64), nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("reference_period", sa.String(64), nullable=True),
        sa.Column("importance", sa.Integer(), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("previous_value", sa.Numeric(24, 6), nullable=True),
        sa.Column("forecast_value", sa.Numeric(24, 6), nullable=True),
        sa.Column("actual_value", sa.Numeric(24, 6), nullable=True),
        sa.Column("unit", sa.String(64), nullable=True),
        sa.Column("source_url", sa.String(512), nullable=False),
        sa.Column("metadata_json", json_type, nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "provider", "external_event_id", name="uq_economic_calendar_events_provider_external_id"
        ),
    )
    op.create_index(
        "ix_economic_calendar_events_scheduled_at", "economic_calendar_events", ["scheduled_at"]
    )


def downgrade():
    op.drop_index("ix_economic_calendar_events_scheduled_at", table_name="economic_calendar_events")
    op.drop_table("economic_calendar_events")
