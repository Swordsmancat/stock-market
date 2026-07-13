"""Add official disclosure metadata."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0017_official_disclosures"
down_revision = "0016_daily_bar_provenance"
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
    op.create_table(
        "official_disclosures",
        sa.Column("id", _uuid_type(), primary_key=True, server_default=_uuid_default()),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_document_id", sa.String(128), nullable=False),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("company_name", sa.String(256), nullable=True),
        sa.Column("title", sa.String(1024), nullable=False),
        sa.Column("category", sa.String(128), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_url", sa.String(2048), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dedupe_hash", sa.String(64), nullable=False),
        sa.Column("metadata_json", _json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "source",
            "source_document_id",
            name="uq_official_disclosures_source_document",
        ),
    )
    op.create_index(
        "ix_official_disclosures_symbol",
        "official_disclosures",
        ["symbol"],
    )


def downgrade():
    op.drop_index("ix_official_disclosures_symbol", table_name="official_disclosures")
    op.drop_table("official_disclosures")
