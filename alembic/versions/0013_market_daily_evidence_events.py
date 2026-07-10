"""Add persisted market daily evidence events."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0013_market_daily_evidence_events"
down_revision = "0012_research_briefs"
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
    op.create_table(
        "market_daily_evidence_events",
        sa.Column("id", _uuid_type(), primary_key=True, server_default=_uuid_default()),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("identity", sa.String(256), nullable=False),
        sa.Column("identity_name", sa.String(512), nullable=True),
        sa.Column("market", sa.String(32), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("source", sa.String(512), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("is_citable", sa.Boolean(), nullable=False),
        sa.Column("payload_json", _json_type(), nullable=False),
        sa.Column("availability_json", _json_type(), nullable=False),
        sa.Column("provider_capabilities_json", _json_type(), nullable=False),
        sa.Column("diagnostics_json", _json_type(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "provider",
            "event_type",
            "identity",
            "market",
            "trade_date",
            name="uq_market_daily_evidence_event_identity",
        ),
    )


def downgrade():
    op.drop_table("market_daily_evidence_events")
