"""Add source configuration and dataset import history.

Revision ID: 0004_phase3_imports
Revises: 0003_phase2_metadata_tables
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004_phase3_imports"
down_revision: str | None = "0003_phase2_metadata_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("data_sources", sa.Column("description", sa.String(500)))
    op.add_column("data_sources", sa.Column("connection_ref", sa.String(80)))
    op.create_table(
        "dataset_imports",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("data_sources.id", ondelete="SET NULL")),
        sa.Column("dataset_id", sa.Uuid(), sa.ForeignKey("datasets.id", ondelete="SET NULL")),
        sa.Column("source_name", sa.String(120), nullable=False),
        sa.Column("source_type", sa.String(80), nullable=False),
        sa.Column("dataset_name", sa.String(120), nullable=False),
        sa.Column("schema_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("records_received", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.String(500)),
        sa.Column("raw_path", sa.String(100)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')", name="ck_dataset_imports_status"
        ),
        sa.CheckConstraint("records_received >= 0", name="ck_dataset_imports_records_nonnegative"),
    )


def downgrade() -> None:
    op.drop_table("dataset_imports")
    op.drop_column("data_sources", "connection_ref")
    op.drop_column("data_sources", "description")
