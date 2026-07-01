"""Add portfolios and portfolio_positions tables."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_portfolios"
down_revision = "0006_task_run_celery_id"
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
    uuid_default = _uuid_default()

    op.create_table(
        "portfolios",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("base_currency", sa.String(8), nullable=False),
        sa.Column("risk_profile", sa.String(64)),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "portfolio_positions",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("portfolio_id", uuid_type, sa.ForeignKey("portfolios.id"), nullable=False),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("market", sa.String(32), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 4), nullable=False),
        sa.Column("avg_cost", sa.Numeric(20, 6), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("portfolio_id", "symbol", "market", name="uq_portfolio_positions_identity"),
    )


def downgrade():
    op.drop_table("portfolio_positions")
    op.drop_table("portfolios")
