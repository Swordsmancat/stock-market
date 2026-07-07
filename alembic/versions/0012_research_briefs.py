"""Add research brief inbox."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012_research_briefs"
down_revision = "0011_research_source_notes"
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
        "research_briefs",
        sa.Column("id", _uuid_type(), primary_key=True, server_default=_uuid_default()),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("brief_type", sa.String(64), nullable=False),
        sa.Column("scope_json", _json_type(), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("citations_json", _json_type(), nullable=False),
        sa.Column("source_summary_json", _json_type(), nullable=False),
        sa.Column("diagnostics_json", _json_type(), nullable=False),
        sa.Column("model_json", _json_type(), nullable=False),
        sa.Column("safety_json", _json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("research_briefs")
