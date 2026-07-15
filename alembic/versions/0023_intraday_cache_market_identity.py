"""Scope intraday cache identity to an exact instrument."""

from alembic import op
import sqlalchemy as sa


revision = "0023_intraday_cache_market_identity"
down_revision = "0022_research_shortlist_task_run"
branch_labels = None
depends_on = None


OLD_CONSTRAINT = "uq_intraday_minute_cache_provider_symbol_date_timeframe"
NEW_CONSTRAINT = "uq_intraday_cache_instrument_provider_symbol_date_timeframe"
IDENTITY_COLUMNS = [
    "instrument_id",
    "provider",
    "symbol",
    "trade_date",
    "timeframe",
]


def upgrade():
    with op.batch_alter_table("intraday_minute_cache_entries") as batch_op:
        batch_op.drop_constraint(OLD_CONSTRAINT, type_="unique")
        batch_op.create_unique_constraint(NEW_CONSTRAINT, IDENTITY_COLUMNS)


def downgrade():
    bind = op.get_bind()
    duplicate_identity = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM intraday_minute_cache_entries
            GROUP BY provider, symbol, trade_date, timeframe
            HAVING COUNT(DISTINCT instrument_id) > 1
            LIMIT 1
            """
        )
    ).first()
    if duplicate_identity is not None:
        raise RuntimeError(
            "Cannot downgrade intraday cache identity while exact-market "
            "cache rows share the legacy provider/symbol/date/timeframe key."
        )
    with op.batch_alter_table("intraday_minute_cache_entries") as batch_op:
        batch_op.drop_constraint(NEW_CONSTRAINT, type_="unique")
        batch_op.create_unique_constraint(
            OLD_CONSTRAINT,
            ["provider", "symbol", "trade_date", "timeframe"],
        )
