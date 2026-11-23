"""Add the Phase 5 analytical warehouse star schema.

Revision ID: 0006_phase5_warehouse
Revises: 0005_phase4_transformations
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0006_phase5_warehouse"
down_revision: str | None = "0005_phase4_transformations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "warehouse_loads",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "transformation_run_id",
            sa.Uuid(),
            sa.ForeignKey("transformation_runs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="running"),
        sa.Column("records_received", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_loaded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("records_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_details", sa.String(500)),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status IN ('running', 'succeeded', 'failed', 'warning')",
            name="ck_warehouse_loads_status",
        ),
        sa.CheckConstraint(
            "records_received >= 0 AND records_loaded >= 0 AND records_skipped >= 0",
            name="ck_warehouse_loads_counts",
        ),
    )
    op.create_index("ix_warehouse_loads_transformation_run_id", "warehouse_loads", ["transformation_run_id"])

    op.create_table(
        "dim_beneficiary",
        sa.Column("beneficiary_key", sa.Integer(), primary_key=True),
        sa.Column("beneficiary_id", sa.String(80), nullable=False, unique=True),
        sa.Column("gender", sa.String(32)),
        sa.Column("age_group", sa.String(32)),
        sa.Column("province", sa.String(80)),
        sa.Column("registration_date", sa.Date()),
    )
    op.create_index("ix_dim_beneficiary_beneficiary_id", "dim_beneficiary", ["beneficiary_id"])

    op.create_table(
        "dim_programme",
        sa.Column("programme_key", sa.Integer(), primary_key=True),
        sa.Column("programme_id", sa.String(120), nullable=False, unique=True),
        sa.Column("programme_name", sa.String(120), nullable=False),
        sa.Column("programme_category", sa.String(80)),
        sa.Column("programme_status", sa.String(16)),
    )
    op.create_index("ix_dim_programme_programme_id", "dim_programme", ["programme_id"])

    op.create_table(
        "dim_location",
        sa.Column("location_key", sa.Integer(), primary_key=True),
        sa.Column("province", sa.String(80), nullable=False),
        sa.Column("district", sa.String(120)),
        sa.Column("municipality", sa.String(120)),
        sa.Column("location_name", sa.String(120)),
        sa.UniqueConstraint(
            "province", "district", "municipality", "location_name",
            name="uq_dim_location_natural",
        ),
    )

    op.create_table(
        "dim_date",
        sa.Column("date_key", sa.Integer(), primary_key=True),
        sa.Column("full_date", sa.Date(), nullable=False, unique=True),
        sa.Column("day", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("month_name", sa.String(20), nullable=False),
        sa.Column("quarter", sa.Integer(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
    )
    op.create_index("ix_dim_date_full_date", "dim_date", ["full_date"])

    op.create_table(
        "dim_organisation",
        sa.Column("organisation_key", sa.Integer(), primary_key=True),
        sa.Column("organisation_id", sa.String(120), nullable=False, unique=True),
        sa.Column("organisation_name", sa.String(120), nullable=False),
        sa.Column("organisation_type", sa.String(80)),
    )
    op.create_index("ix_dim_organisation_organisation_id", "dim_organisation", ["organisation_id"])

    op.create_table(
        "dim_indicator",
        sa.Column("indicator_key", sa.Integer(), primary_key=True),
        sa.Column("indicator_id", sa.String(120), nullable=False, unique=True),
        sa.Column("indicator_name", sa.String(160), nullable=False),
        sa.Column("indicator_category", sa.String(80)),
        sa.Column("measurement_unit", sa.String(40)),
        sa.Column("description", sa.String(500)),
    )
    op.create_index("ix_dim_indicator_indicator_id", "dim_indicator", ["indicator_id"])

    op.create_table(
        "fact_beneficiary_participation",
        sa.Column("participation_key", sa.Integer(), primary_key=True),
        sa.Column("beneficiary_key", sa.Integer(), sa.ForeignKey("dim_beneficiary.beneficiary_key"), nullable=False),
        sa.Column("programme_key", sa.Integer(), sa.ForeignKey("dim_programme.programme_key"), nullable=False),
        sa.Column("location_key", sa.Integer(), sa.ForeignKey("dim_location.location_key"), nullable=False),
        sa.Column("date_key", sa.Integer(), sa.ForeignKey("dim_date.date_key"), nullable=False),
        sa.Column("participation_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("attendance_status", sa.String(32)),
        sa.UniqueConstraint(
            "beneficiary_key", "programme_key", "location_key", "date_key",
            name="uq_fact_participation_grain",
        ),
    )
    op.create_table(
        "fact_programme_outcomes",
        sa.Column("outcome_key", sa.Integer(), primary_key=True),
        sa.Column("programme_key", sa.Integer(), sa.ForeignKey("dim_programme.programme_key"), nullable=False),
        sa.Column("location_key", sa.Integer(), sa.ForeignKey("dim_location.location_key"), nullable=False),
        sa.Column("indicator_key", sa.Integer(), sa.ForeignKey("dim_indicator.indicator_key"), nullable=False),
        sa.Column("date_key", sa.Integer(), sa.ForeignKey("dim_date.date_key"), nullable=False),
        sa.Column("baseline_value", sa.Float()),
        sa.Column("target_value", sa.Float()),
        sa.Column("actual_value", sa.Float()),
        sa.Column("achievement_percentage", sa.Float()),
        sa.UniqueConstraint(
            "programme_key", "location_key", "indicator_key", "date_key",
            name="uq_fact_programme_outcome_grain",
        ),
    )
    op.create_table(
        "fact_expenditure",
        sa.Column("expenditure_key", sa.Integer(), primary_key=True),
        sa.Column("programme_key", sa.Integer(), sa.ForeignKey("dim_programme.programme_key"), nullable=False),
        sa.Column("organisation_key", sa.Integer(), sa.ForeignKey("dim_organisation.organisation_key"), nullable=False),
        sa.Column("location_key", sa.Integer(), sa.ForeignKey("dim_location.location_key"), nullable=False),
        sa.Column("date_key", sa.Integer(), sa.ForeignKey("dim_date.date_key"), nullable=False),
        sa.Column("budget_amount", sa.Float()),
        sa.Column("actual_expenditure", sa.Float()),
        sa.Column("remaining_budget", sa.Float()),
    )
    op.create_table(
        "fact_assessments",
        sa.Column("assessment_key", sa.Integer(), primary_key=True),
        sa.Column("beneficiary_key", sa.Integer(), sa.ForeignKey("dim_beneficiary.beneficiary_key"), nullable=False),
        sa.Column("programme_key", sa.Integer(), sa.ForeignKey("dim_programme.programme_key"), nullable=False),
        sa.Column("indicator_key", sa.Integer(), sa.ForeignKey("dim_indicator.indicator_key"), nullable=False),
        sa.Column("date_key", sa.Integer(), sa.ForeignKey("dim_date.date_key"), nullable=False),
        sa.Column("assessment_score", sa.Float()),
        sa.Column("assessment_type", sa.String(80)),
    )


def downgrade() -> None:
    for table in (
        "fact_assessments",
        "fact_expenditure",
        "fact_programme_outcomes",
        "fact_beneficiary_participation",
        "dim_indicator",
        "dim_organisation",
        "dim_date",
        "dim_location",
        "dim_programme",
        "dim_beneficiary",
    ):
        op.drop_table(table)
    op.drop_index("ix_warehouse_loads_transformation_run_id", table_name="warehouse_loads")
    op.drop_table("warehouse_loads")
