"""Add organisation, location and dataset metadata tables.

Revision ID: 0003_phase2_metadata_tables
Revises: 0002_database_ingestion_jobs
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_phase2_metadata_tables"
down_revision: str | None = "0002_database_ingestion_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "organisations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_table(
        "locations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("province", sa.String(80), nullable=False),
        sa.Column("district", sa.String(120)),
        sa.Column("area", sa.String(120)),
    )
    op.create_table(
        "datasets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("description", sa.String(500)),
        sa.Column("source_id", sa.Uuid(), sa.ForeignKey("data_sources.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("datasets")
    op.drop_table("locations")
    op.drop_table("organisations")
