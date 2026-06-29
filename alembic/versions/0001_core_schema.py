from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_core_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "markets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("trading_calendar_code", sa.String(64)),
    )
    op.create_table(
        "exchanges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("market_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("markets.id"), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
    )
    op.create_table(
        "instruments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("market_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("markets.id"), nullable=False),
        sa.Column("exchange_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("exchanges.id")),
        sa.Column("asset_type", sa.String(32), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("market_id", "symbol", name="uq_instruments_market_symbol"),
    )
    op.create_table(
        "bars_1d",
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(20, 6), nullable=False),
        sa.Column("high", sa.Numeric(20, 6), nullable=False),
        sa.Column("low", sa.Numeric(20, 6), nullable=False),
        sa.Column("close", sa.Numeric(20, 6), nullable=False),
        sa.Column("volume", sa.Numeric(24, 4), nullable=False),
        sa.Column("amount", sa.Numeric(24, 4)),
        sa.PrimaryKeyConstraint("instrument_id", "trade_date"),
    )
    op.create_table(
        "bars_1m",
        sa.Column("instrument_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(20, 6), nullable=False),
        sa.Column("high", sa.Numeric(20, 6), nullable=False),
        sa.Column("low", sa.Numeric(20, 6), nullable=False),
        sa.Column("close", sa.Numeric(20, 6), nullable=False),
        sa.Column("volume", sa.Numeric(24, 4), nullable=False),
        sa.Column("amount", sa.Numeric(24, 4)),
        sa.PrimaryKeyConstraint("instrument_id", "ts"),
    )
    op.execute("SELECT create_hypertable('bars_1m', 'ts', if_not_exists => TRUE)")


def downgrade():
    op.drop_table("bars_1m")
    op.drop_table("bars_1d")
    op.drop_table("instruments")
    op.drop_table("exchanges")
    op.drop_table("markets")
