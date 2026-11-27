"""Phase 7 data quality, governance and audit tables."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Uuid,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base

DIMENSIONS = ("completeness", "validity", "uniqueness", "consistency", "timeliness", "accuracy")
SEVERITIES = ("low", "medium", "high", "critical")
ISSUE_STATUSES = ("Open", "Investigating", "In Progress", "Resolved", "Accepted Risk")
CLASSIFICATIONS = ("public", "internal", "confidential", "restricted")


def _now() -> datetime:
    return datetime.now(UTC)


def _pk() -> Mapped[UUID]:
    return mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)


def _in(column: str, values: tuple[str, ...]) -> str:
    return f"{column} IN ({', '.join(repr(value) for value in values)})"


class QualityRule(Base):
    __tablename__ = "quality_rules"

    id: Mapped[UUID] = _pk()
    name: Mapped[str] = mapped_column(String(160))
    dataset_key: Mapped[str] = mapped_column(String(200), index=True)
    dimension: Mapped[str] = mapped_column(String(20))
    rule_type: Mapped[str] = mapped_column(String(40))
    column_name: Mapped[str | None] = mapped_column(String(120))
    params: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    warn_threshold: Mapped[float] = mapped_column(Float, default=98.0)
    fail_threshold: Mapped[float] = mapped_column(Float, default=90.0)
    severity: Mapped[str] = mapped_column(String(10), default="medium")
    enabled: Mapped[bool] = mapped_column(default=True)
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        CheckConstraint(_in("dimension", DIMENSIONS), name="ck_quality_rules_dimension"),
        CheckConstraint(_in("severity", SEVERITIES), name="ck_quality_rules_severity"),
        CheckConstraint(
            "fail_threshold >= 0 AND warn_threshold <= 100 AND fail_threshold <= warn_threshold",
            name="ck_quality_rules_thresholds",
        ),
    )


class QualityRuleRun(Base):
    __tablename__ = "quality_rule_runs"

    id: Mapped[UUID] = _pk()
    batch_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), index=True)
    rule_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("quality_rules.id", ondelete="SET NULL"), nullable=True, index=True
    )
    dataset_key: Mapped[str] = mapped_column(String(200), index=True)
    dimension: Mapped[str] = mapped_column(String(20))
    rule_name: Mapped[str] = mapped_column(String(160))
    records_evaluated: Mapped[int] = mapped_column(Integer, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, default=0)
    pass_rate: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16))
    detail: Mapped[str | None] = mapped_column(String(300))
    failed_sample: Mapped[list[object]] = mapped_column(JSON, default=list)
    transformation_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("transformation_runs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    trigger: Mapped[str] = mapped_column(String(16), default="manual")
    executed_by: Mapped[str | None] = mapped_column(String(320))
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    __table_args__ = (
        CheckConstraint(
            _in("status", ("pass", "warning", "fail", "not_applicable", "error")),
            name="ck_quality_rule_runs_status",
        ),
    )


class QualityIssue(Base):
    __tablename__ = "quality_issues"

    id: Mapped[UUID] = _pk()
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(1000))
    dataset_key: Mapped[str] = mapped_column(String(200), index=True)
    source_name: Mapped[str | None] = mapped_column(String(120))
    rule_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("quality_rules.id", ondelete="SET NULL"), nullable=True
    )
    transformation_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("transformation_runs.id", ondelete="SET NULL"), nullable=True
    )
    severity: Mapped[str] = mapped_column(String(10), default="medium")
    affected_records: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="Open", index=True)
    assigned_to: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolution_notes: Mapped[str | None] = mapped_column(String(1000))
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(_in("status", ISSUE_STATUSES), name="ck_quality_issues_status"),
        CheckConstraint(_in("severity", SEVERITIES), name="ck_quality_issues_severity"),
        CheckConstraint("affected_records >= 0", name="ck_quality_issues_affected"),
    )


class QualityIssueEvent(Base):
    __tablename__ = "quality_issue_events"

    id: Mapped[UUID] = _pk()
    issue_id: Mapped[UUID] = mapped_column(
        ForeignKey("quality_issues.id", ondelete="CASCADE"), index=True
    )
    event: Mapped[str] = mapped_column(String(40))
    from_status: Mapped[str | None] = mapped_column(String(16))
    to_status: Mapped[str | None] = mapped_column(String(16))
    note: Mapped[str | None] = mapped_column(String(1000))
    actor: Mapped[str | None] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CatalogueEntry(Base):
    """Editable business metadata; technical metadata is derived live."""

    __tablename__ = "catalogue_entries"

    id: Mapped[UUID] = _pk()
    dataset_key: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str | None] = mapped_column(String(1000))
    owner_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    steward_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    classification: Mapped[str | None] = mapped_column(String(16))
    column_definitions: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    updated_by: Mapped[str | None] = mapped_column(String(320))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        CheckConstraint(
            "classification IS NULL OR " + _in("classification", CLASSIFICATIONS),
            name="ck_catalogue_entries_classification",
        ),
    )


class GovernancePolicy(Base):
    __tablename__ = "governance_policies"

    id: Mapped[UUID] = _pk()
    name: Mapped[str] = mapped_column(String(160))
    dataset_key: Mapped[str] = mapped_column(String(200), index=True)
    classification: Mapped[str] = mapped_column(String(16))
    purpose: Mapped[str | None] = mapped_column(String(500))
    retention_days: Mapped[int | None] = mapped_column(Integer)
    review_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    archival_status: Mapped[str] = mapped_column(String(16), default="active")
    owner_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(12), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        CheckConstraint(_in("classification", CLASSIFICATIONS), name="ck_policies_classification"),
        CheckConstraint(
            _in("archival_status", ("active", "archive_due", "archived")),
            name="ck_policies_archival",
        ),
        CheckConstraint(_in("status", ("active", "inactive")), name="ck_policies_status"),
        CheckConstraint(
            "retention_days IS NULL OR retention_days > 0", name="ck_policies_retention"
        ),
    )


class AccessRequest(Base):
    __tablename__ = "access_requests"

    id: Mapped[UUID] = _pk()
    dataset_key: Mapped[str] = mapped_column(String(200), index=True)
    requester_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    reason: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(10), default="pending")
    decided_by: Mapped[str | None] = mapped_column(String(320))
    decision_note: Mapped[str | None] = mapped_column(String(500))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            _in("status", ("pending", "approved", "denied")), name="ck_access_requests_status"
        ),
    )


class GovernanceSetting(Base):
    __tablename__ = "governance_settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditEvent(Base):
    """Append-only audit trail; updates and deletes are rejected by the ORM."""

    __tablename__ = "audit_events"

    id: Mapped[UUID] = _pk()
    user_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), index=True)
    actor: Mapped[str] = mapped_column(String(320))
    action: Mapped[str] = mapped_column(String(80), index=True)
    resource_type: Mapped[str] = mapped_column(String(60), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(200))
    outcome: Mapped[str] = mapped_column(String(10), default="success")
    details: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)

    __table_args__ = (
        CheckConstraint(_in("outcome", ("success", "denied", "failure")), name="ck_audit_outcome"),
    )


@event.listens_for(AuditEvent, "before_update")
@event.listens_for(AuditEvent, "before_delete")
def _reject_audit_mutation(*_args: object) -> None:
    raise PermissionError("Audit events are immutable.")
