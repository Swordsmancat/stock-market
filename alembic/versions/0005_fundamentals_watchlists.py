from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_fundamentals_watchlists"
down_revision = "0004_task_runs"
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
        "fundamental_snapshots",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("pe_ratio", sa.Numeric(20, 6), nullable=False),
        sa.Column("revenue_growth", sa.Numeric(12, 6), nullable=False),
        sa.Column("net_margin", sa.Numeric(12, 6), nullable=False),
        sa.Column("debt_to_assets", sa.Numeric(12, 6), nullable=False),
        sa.Column("source", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("symbol", "as_of", name="uq_fundamental_snapshots_symbol_as_of"),
    )
    op.create_table(
        "watchlists",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "watchlist_items",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("watchlist_id", uuid_type, sa.ForeignKey("watchlists.id"), nullable=False),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("market", sa.String(32), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("alert_rules", _json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("watchlist_id", "symbol", "market", name="uq_watchlist_items_identity"),
    )


def downgrade():
    op.drop_table("watchlist_items")
    op.drop_table("watchlists")
    op.drop_table("fundamental_snapshots")
