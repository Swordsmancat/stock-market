"""Preserve missing fundamental metrics as null."""

from alembic import op
import sqlalchemy as sa


revision = "0024_nullable_fundamental_metrics"
down_revision = "0023_intraday_cache_market_identity"
branch_labels = None
depends_on = None


METRIC_TYPES = {
    "pe_ratio": sa.Numeric(20, 6),
    "revenue_growth": sa.Numeric(12, 6),
    "net_margin": sa.Numeric(12, 6),
    "debt_to_assets": sa.Numeric(12, 6),
}
LEGACY_SENTINEL_SOURCES = ("akshare", "yfinance", "tushare")


def upgrade():
    with op.batch_alter_table("fundamental_snapshots") as batch_op:
        for column, column_type in METRIC_TYPES.items():
            batch_op.alter_column(
                column,
                existing_type=column_type,
                nullable=True,
            )

    bind = op.get_bind()
    for column in METRIC_TYPES:
        bind.execute(
            sa.text(
                f"""
                UPDATE fundamental_snapshots
                SET {column} = NULL
                WHERE source IN :sources AND {column} = 0
                """
            ).bindparams(sa.bindparam("sources", expanding=True)),
            {"sources": LEGACY_SENTINEL_SOURCES},
        )


def downgrade():
    bind = op.get_bind()
    for column in METRIC_TYPES:
        bind.execute(
            sa.text(
                f"UPDATE fundamental_snapshots SET {column} = 0 WHERE {column} IS NULL"
            )
        )

    with op.batch_alter_table("fundamental_snapshots") as batch_op:
        for column, column_type in METRIC_TYPES.items():
            batch_op.alter_column(
                column,
                existing_type=column_type,
                nullable=False,
            )
