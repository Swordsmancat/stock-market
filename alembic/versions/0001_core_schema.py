from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_core_schema"
down_revision = None
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

    if _is_postgresql():
        op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
        op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "markets",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("trading_calendar_code", sa.String(64)),
    )
    op.create_table(
        "exchanges",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("market_id", uuid_type, sa.ForeignKey("markets.id"), nullable=False),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
    )
    op.create_table(
        "instruments",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("market_id", uuid_type, sa.ForeignKey("markets.id"), nullable=False),
        sa.Column("exchange_id", uuid_type, sa.ForeignKey("exchanges.id")),
        sa.Column("asset_type", sa.String(32), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("market_id", "symbol", name="uq_instruments_market_symbol"),
    )
    op.create_table(
        "data_sources",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("name", sa.String(128), nullable=False, unique=True),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("100")),
        sa.Column("license_scope", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_table(
        "bars_1d",
        sa.Column("instrument_id", uuid_type, sa.ForeignKey("instruments.id"), nullable=False),
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
        sa.Column("instrument_id", uuid_type, sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("open", sa.Numeric(20, 6), nullable=False),
        sa.Column("high", sa.Numeric(20, 6), nullable=False),
        sa.Column("low", sa.Numeric(20, 6), nullable=False),
        sa.Column("close", sa.Numeric(20, 6), nullable=False),
        sa.Column("volume", sa.Numeric(24, 4), nullable=False),
        sa.Column("amount", sa.Numeric(24, 4)),
        sa.PrimaryKeyConstraint("instrument_id", "ts"),
    )
    op.create_table(
        "technical_indicators",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("instrument_id", uuid_type, sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column("timeframe", sa.String(16), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("indicator_code", sa.String(64), nullable=False),
        sa.Column("params", _json_type(), nullable=False),
        sa.Column("value_json", _json_type(), nullable=False),
    )

    if _is_postgresql():
        op.execute("SELECT create_hypertable('bars_1m', 'ts', if_not_exists => TRUE)")


def downgrade():
    op.drop_table("technical_indicators")
    op.drop_table("bars_1m")
    op.drop_table("bars_1d")
    op.drop_table("data_sources")
    op.drop_table("instruments")
    op.drop_table("exchanges")
    op.drop_table("markets")
