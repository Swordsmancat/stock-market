"""Add generation TaskRun lineage to research shortlist runs."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0022_research_shortlist_task_run"
down_revision = "0021_research_shortlist_outcomes"
branch_labels = None
depends_on = None


def _is_postgresql():
    bind = op.get_bind()
    return bind is not None and bind.dialect.name == "postgresql"


def _uuid_type():
    if _is_postgresql():
        return postgresql.UUID(as_uuid=True)
    return sa.String(36)


def upgrade():
    with op.batch_alter_table("research_shortlist_runs") as batch_op:
        batch_op.add_column(
            sa.Column("generation_task_run_id", _uuid_type(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_research_shortlist_runs_generation_task_run_id_task_runs",
            "task_runs",
            ["generation_task_run_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_research_shortlist_runs_generation_task_run_id",
            ["generation_task_run_id"],
        )


def downgrade():
    with op.batch_alter_table("research_shortlist_runs") as batch_op:
        batch_op.drop_index(
            "ix_research_shortlist_runs_generation_task_run_id"
        )
        batch_op.drop_constraint(
            "fk_research_shortlist_runs_generation_task_run_id_task_runs",
            type_="foreignkey",
        )
        batch_op.drop_column("generation_task_run_id")
