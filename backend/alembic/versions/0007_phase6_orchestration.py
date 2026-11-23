"""Add orchestration run correlation and audit metadata.

Revision ID: 0007_phase6_orchestration
Revises: 0006_phase5_warehouse
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007_phase6_orchestration"
down_revision: str | None = "0006_phase5_warehouse"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "orchestration_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("airflow_dag_id", sa.String(120), nullable=False),
        sa.Column("airflow_run_id", sa.String(250), nullable=False, unique=True),
        sa.Column(
            "pipeline_run_id",
            sa.Uuid(),
            sa.ForeignKey("pipeline_runs.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "dataset_import_id",
            sa.Uuid(),
            sa.ForeignKey("dataset_imports.id", ondelete="SET NULL"),
        ),
        sa.Column("status", sa.String(32), nullable=False, server_default="queued"),
        sa.Column("trigger_type", sa.String(16), nullable=False, server_default="manual"),
        sa.Column("execution_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("records_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_accepted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_rejected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_details", sa.String(500)),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'success', 'failed', 'up_for_retry', 'cancelled')",
            name="ck_orchestration_runs_status",
        ),
        sa.CheckConstraint(
            "trigger_type IN ('manual', 'scheduled')",
            name="ck_orchestration_runs_trigger_type",
        ),
    )
    op.create_index("ix_orchestration_runs_airflow_dag_id", "orchestration_runs", ["airflow_dag_id"])
    op.create_index("ix_orchestration_runs_execution_date", "orchestration_runs", ["execution_date"])


def downgrade() -> None:
    op.drop_index("ix_orchestration_runs_execution_date", table_name="orchestration_runs")
    op.drop_index("ix_orchestration_runs_airflow_dag_id", table_name="orchestration_runs")
    op.drop_table("orchestration_runs")
