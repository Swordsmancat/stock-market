"""add stored fundamental company metadata

Revision ID: 0027_fundamental_company_metadata
Revises: 0026_industry_daily_rankings
"""

from alembic import op
import sqlalchemy as sa


revision = "0027_fundamental_company_metadata"
down_revision = "0026_industry_daily_rankings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "fundamental_snapshots",
        sa.Column(
            "company_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.alter_column("fundamental_snapshots", "company_json", server_default=None)


def downgrade() -> None:
    op.drop_column("fundamental_snapshots", "company_json")
