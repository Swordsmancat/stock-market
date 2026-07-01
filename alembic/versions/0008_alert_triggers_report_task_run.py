"""Add alert_triggers and generated_reports.task_run_id."""

from alembic import op
import sqlalchemy as sa

revision = "0008_alerts_report_run"
down_revision = "0007_portfolios"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "alert_triggers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("symbol", sa.String(length=64), nullable=False),
        sa.Column("market", sa.String(length=32), nullable=False),
        sa.Column("rule_key", sa.String(length=64), nullable=False),
        sa.Column("threshold", sa.Numeric(precision=20, scale=6), nullable=False),
        sa.Column("observed_value", sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column(
            "triggered_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_triggers_symbol", "alert_triggers", ["symbol"])
    op.create_index("ix_alert_triggers_triggered_at", "alert_triggers", ["triggered_at"])

    op.add_column(
        "generated_reports",
        sa.Column("task_run_id", sa.Uuid(), sa.ForeignKey("task_runs.id"), nullable=True),
    )


def downgrade():
    op.drop_column("generated_reports", "task_run_id")
    op.drop_index("ix_alert_triggers_triggered_at", table_name="alert_triggers")
    op.drop_index("ix_alert_triggers_symbol", table_name="alert_triggers")
    op.drop_table("alert_triggers")
