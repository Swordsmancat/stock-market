"""Add intraday minute cache metadata."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010_intraday_minute_cache_entries"
down_revision = "0009_market_indicators"
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
        "intraday_minute_cache_entries",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("instrument_id", uuid_type, sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("timeframe", sa.String(16), nullable=False),
        sa.Column("source", sa.String(128), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("first_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cached_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "provider",
            "symbol",
            "trade_date",
            "timeframe",
            name="uq_intraday_minute_cache_provider_symbol_date_timeframe",
        ),
    )


def downgrade():
    op.drop_table("intraday_minute_cache_entries")
