from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_generated_reports"
down_revision = "0002_news_sentiment"
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
        "generated_reports",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("report_type", sa.String(64), nullable=False),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=False),
        sa.Column("citations", _json_type(), nullable=False),
        sa.Column("source_summary", _json_type(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("generated_reports")
