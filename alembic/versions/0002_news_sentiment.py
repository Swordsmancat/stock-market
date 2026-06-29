from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_news_sentiment"
down_revision = "0001_core_schema"
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


def upgrade():
    uuid_type = _uuid_type()
    uuid_default = _uuid_default()

    op.create_table(
        "news_articles",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("url", sa.String(1024), nullable=False),
        sa.Column("source", sa.String(128), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("dedupe_hash", sa.String(64), nullable=False, unique=True),
    )
    op.create_table(
        "sentiment_signals",
        sa.Column("id", uuid_type, primary_key=True, server_default=uuid_default),
        sa.Column("article_id", uuid_type, sa.ForeignKey("news_articles.id"), nullable=False),
        sa.Column("symbol", sa.String(64), nullable=False),
        sa.Column("sentiment", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    op.drop_table("sentiment_signals")
    op.drop_table("news_articles")
