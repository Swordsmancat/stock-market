"""add asset-aware ETF and index universe identity

Revision ID: 0028_etf_index_universe_identity
Revises: 0027_fundamental_company_metadata
"""

from alembic import op
import sqlalchemy as sa


revision = "0028_etf_index_universe_identity"
down_revision = "0027_fundamental_company_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "instrument_universe_syncs",
        sa.Column(
            "asset_type",
            sa.String(length=32),
            nullable=False,
            server_default="stock",
        ),
    )
    with op.batch_alter_table("instrument_universe_syncs") as batch_op:
        batch_op.alter_column("asset_type", server_default=None)
    op.create_index(
        "ix_instrument_universe_syncs_lookup",
        "instrument_universe_syncs",
        ["market", "provider", "asset_type", "created_at"],
    )
    with op.batch_alter_table("instruments") as batch_op:
        batch_op.drop_constraint("uq_instruments_market_symbol", type_="unique")
        batch_op.create_unique_constraint(
            "uq_instruments_market_symbol_asset_type",
            ["market_id", "symbol", "asset_type"],
        )


def downgrade() -> None:
    with op.batch_alter_table("instruments") as batch_op:
        batch_op.drop_constraint(
            "uq_instruments_market_symbol_asset_type",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_instruments_market_symbol",
            ["market_id", "symbol"],
        )
    op.drop_index(
        "ix_instrument_universe_syncs_lookup",
        table_name="instrument_universe_syncs",
    )
    op.drop_column("instrument_universe_syncs", "asset_type")
