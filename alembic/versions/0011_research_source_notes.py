"""Add research source notebook."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0011_research_source_notes"
down_revision = "0010_intraday_minute_cache_entries"
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
        "research_source_notes",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("source_url", sa.String(1024), nullable=True),
        sa.Column("source_name", sa.String(256), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("symbols_json", _json_type(), nullable=False),
        sa.Column("tags_json", _json_type(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("as_of", sa.Date(), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("ai_follow_up", sa.Text(), nullable=True),
        sa.Column("review_status", sa.String(32), nullable=False),
        sa.Column("is_citable", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", _json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("research_source_notes")
