"""Add persistent ETL transformation history.

Revision ID: 0005_phase4_transformations
Revises: 0004_phase3_imports
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005_phase4_transformations"
down_revision: str | None = "0004_phase3_imports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "transformation_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "dataset_import_id",
            sa.Uuid(),
            sa.ForeignKey("dataset_imports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "dataset_id",
            sa.Uuid(),
            sa.ForeignKey("datasets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("pipeline_name", sa.String(120), nullable=False),
        sa.Column("schema_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="running"),
        sa.Column("records_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_rejected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duplicate_records", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("missing_values", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "quality_report",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("error_details", sa.String(500)),
        sa.Column("silver_path", sa.String(200)),
        sa.Column("gold_files", sa.JSON()),
        sa.Column("quarantine_path", sa.String(200)),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed', 'warning')",
            name="ck_transformation_runs_status",
        ),
        sa.CheckConstraint(
            "records_received >= 0 AND records_processed >= 0 AND records_rejected >= 0 "
            "AND duplicate_records >= 0 AND missing_values >= 0",
            name="ck_transformation_runs_counts",
        ),
        sa.CheckConstraint(
            "quality_score >= 0 AND quality_score <= 100",
            name="ck_transformation_runs_quality_score",
        ),
    )
    op.create_index(
        "ix_transformation_runs_dataset_import_id",
        "transformation_runs",
        ["dataset_import_id"],
    )
    op.create_index(
        "ix_transformation_runs_started_at",
        "transformation_runs",
        ["started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_transformation_runs_started_at", table_name="transformation_runs")
    op.drop_index("ix_transformation_runs_dataset_import_id", table_name="transformation_runs")
    op.drop_table("transformation_runs")
