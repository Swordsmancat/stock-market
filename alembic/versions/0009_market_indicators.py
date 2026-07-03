"""Add market indicator storage."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0009_market_indicators"
down_revision = "0008_alerts_report_run"
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
    uuid_default = _uuid_default()

    op.create_table(
        "market_indicators",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("code", sa.String(128), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("region", sa.String(32), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("code", name="uq_market_indicators_code"),
    )
    op.create_table(
        "market_indicator_observations",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("indicator_id", uuid_type, sa.ForeignKey("market_indicators.id"), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(20, 6), nullable=False),
        sa.Column("source", sa.String(512), nullable=False),
        sa.Column("components_json", _json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "indicator_id",
            "as_of",
            name="uq_market_indicator_observations_indicator_as_of",
        ),
    )


def downgrade():
    op.drop_table("market_indicator_observations")
    op.drop_table("market_indicators")
