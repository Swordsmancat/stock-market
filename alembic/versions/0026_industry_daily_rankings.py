"""add stored industry daily rankings

Revision ID: 0026_industry_daily_rankings
Revises: 0025_economic_calendar_events
"""
from alembic import op
import sqlalchemy as sa

revision = "0026_industry_daily_rankings"
down_revision = "0025_economic_calendar_events"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("industry_daily_rankings", sa.Column("id", sa.Uuid(), nullable=False), sa.Column("provider", sa.String(32), nullable=False), sa.Column("taxonomy", sa.String(32), nullable=False), sa.Column("industry_code", sa.String(32), nullable=False), sa.Column("industry_name", sa.String(128), nullable=False), sa.Column("trade_date", sa.Date(), nullable=False), sa.Column("change_percent", sa.Numeric(12, 4), nullable=False), sa.Column("rank", sa.Integer(), nullable=False), sa.Column("source_url", sa.String(512), nullable=False), sa.Column("metadata_json", sa.JSON(), nullable=False), sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("provider", "taxonomy", "industry_code", "trade_date", name="uq_industry_daily_rankings_identity"))
    op.create_index("ix_industry_daily_rankings_date_rank", "industry_daily_rankings", ["trade_date", "rank"])

def downgrade() -> None:
    op.drop_index("ix_industry_daily_rankings_date_rank", table_name="industry_daily_rankings")
    op.drop_table("industry_daily_rankings")
