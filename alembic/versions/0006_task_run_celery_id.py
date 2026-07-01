"""Add celery_task_id to task_runs."""

from alembic import op
import sqlalchemy as sa

revision = "0006_task_run_celery_id"
down_revision = "0005_fundamentals_watchlists"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("task_runs", sa.Column("celery_task_id", sa.String(128), nullable=True))


def downgrade():
    op.drop_column("task_runs", "celery_task_id")
