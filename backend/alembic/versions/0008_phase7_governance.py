"""Add data quality, governance, access and audit tables.

Revision ID: 0008_phase7_governance
Revises: 0007_phase6_orchestration
"""

from collections.abc import Sequence

from alembic import op
from app import governance_models  # noqa: F401
from app.database.base import Base

revision: str = "0008_phase7_governance"
down_revision: str | None = "0007_phase6_orchestration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = [
    "quality_rules",
    "quality_rule_runs",
    "quality_issues",
    "quality_issue_events",
    "catalogue_entries",
    "governance_policies",
    "access_requests",
    "governance_settings",
    "audit_events",
]
OLD_ROLES = "role IN ('admin', 'viewer')"
NEW_ROLES = "role IN ('admin', 'data_owner', 'data_steward', 'data_engineer', 'viewer')"


def upgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint("ck_users_role", "users", NEW_ROLES)
    bind = op.get_bind()
    Base.metadata.create_all(bind, tables=[Base.metadata.tables[name] for name in TABLES])


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind, tables=[Base.metadata.tables[name] for name in reversed(TABLES)])
    op.execute("UPDATE users SET role = 'viewer' WHERE role NOT IN ('admin', 'viewer')")
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint("ck_users_role", "users", OLD_ROLES)
