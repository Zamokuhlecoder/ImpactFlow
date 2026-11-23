from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    role: Mapped[str] = mapped_column(String(16), default="viewer")
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'viewer')", name="ck_users_role"),
    )


class Organisation(Base):
    __tablename__ = "organisations"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    province: Mapped[str] = mapped_column(String(80))
    district: Mapped[str | None] = mapped_column(String(120))
    area: Mapped[str | None] = mapped_column(String(120))


class Programme(Base):
    __tablename__ = "programmes"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    category: Mapped[str] = mapped_column(String(80))
    province: Mapped[str] = mapped_column(String(80))
    target_beneficiaries: Mapped[int] = mapped_column(Integer)
    reached_beneficiaries: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "target_beneficiaries >= 0 AND reached_beneficiaries >= 0",
            name="ck_programmes_beneficiary_counts_nonnegative",
        ),
        CheckConstraint("status IN ('active', 'inactive')", name="ck_programmes_status"),
    )


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    source_type: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(String(500))
    connection_ref: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(16), default="active")
    records_count: Mapped[int] = mapped_column(Integer, default=0)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("records_count >= 0", name="ck_data_sources_records_nonnegative"),
        CheckConstraint(
            "status IN ('active', 'inactive', 'error')", name="ck_data_sources_status"
        ),
    )


class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str | None] = mapped_column(String(500))
    source_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class DatasetImport(Base):
    __tablename__ = "dataset_imports"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    source_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True
    )
    dataset_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True
    )
    source_name: Mapped[str] = mapped_column(String(120))
    source_type: Mapped[str] = mapped_column(String(80))
    dataset_name: Mapped[str] = mapped_column(String(120))
    schema_type: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(16))
    records_received: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(String(500))
    raw_path: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'succeeded', 'failed')", name="ck_dataset_imports_status"
        ),
        CheckConstraint(
            "records_received >= 0", name="ck_dataset_imports_records_nonnegative"
        ),
    )


class TransformationRun(Base):
    __tablename__ = "transformation_runs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    dataset_import_id: Mapped[UUID] = mapped_column(
        ForeignKey("dataset_imports.id", ondelete="CASCADE"), index=True
    )
    dataset_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("datasets.id", ondelete="SET NULL"), nullable=True
    )
    pipeline_name: Mapped[str] = mapped_column(String(120))
    schema_type: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(16), default="running")
    records_received: Mapped[int] = mapped_column(Integer, default=0)
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    records_rejected: Mapped[int] = mapped_column(Integer, default=0)
    duplicate_records: Mapped[int] = mapped_column(Integer, default=0)
    missing_values: Mapped[int] = mapped_column(Integer, default=0)
    quality_score: Mapped[float] = mapped_column(default=0)
    quality_report: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    error_details: Mapped[str | None] = mapped_column(String(500))
    silver_path: Mapped[str | None] = mapped_column(String(200))
    gold_files: Mapped[dict[str, str] | None] = mapped_column(JSON)
    quarantine_path: Mapped[str | None] = mapped_column(String(200))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dataset_import: Mapped[DatasetImport] = relationship()

    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'succeeded', 'failed', 'warning')",
            name="ck_transformation_runs_status",
        ),
        CheckConstraint(
            "records_received >= 0 AND records_processed >= 0 AND records_rejected >= 0 "
            "AND duplicate_records >= 0 AND missing_values >= 0",
            name="ck_transformation_runs_counts",
        ),
        CheckConstraint(
            "quality_score >= 0 AND quality_score <= 100",
            name="ck_transformation_runs_quality_score",
        ),
    )


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    pipeline_name: Mapped[str] = mapped_column(String(120), index=True)
    source_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16))
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[DataSource | None] = relationship()

    __table_args__ = (
        CheckConstraint("records_processed >= 0", name="ck_pipeline_runs_records_nonnegative"),
        CheckConstraint(
            "status IN ('succeeded', 'running', 'failed', 'warning')",
            name="ck_pipeline_runs_status",
        ),
    )


class OrchestrationRun(Base):
    __tablename__ = "orchestration_runs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    airflow_dag_id: Mapped[str] = mapped_column(String(120), index=True)
    airflow_run_id: Mapped[str] = mapped_column(String(250), unique=True, index=True)
    pipeline_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True
    )
    dataset_import_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("dataset_imports.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), default="queued")
    trigger_type: Mapped[str] = mapped_column(String(16), default="manual")
    execution_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    records_accepted: Mapped[int] = mapped_column(Integer, default=0)
    records_rejected: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_details: Mapped[str | None] = mapped_column(String(500))

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'success', 'failed', 'up_for_retry', 'cancelled')",
            name="ck_orchestration_runs_status",
        ),
        CheckConstraint(
            "trigger_type IN ('manual', 'scheduled')",
            name="ck_orchestration_runs_trigger_type",
        ),
    )


class DataQualitySnapshot(Base):
    __tablename__ = "data_quality_snapshots"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    score: Mapped[float]
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="ck_quality_score_range"),
    )


class IngestionRecord(Base):
    __tablename__ = "ingestion_records"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    source_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("data_sources.id", ondelete="SET NULL"), nullable=True
    )
    records_ingested: Mapped[int] = mapped_column(Integer)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    source: Mapped[DataSource | None] = relationship()

    __table_args__ = (
        CheckConstraint("records_ingested >= 0", name="ck_ingestion_records_nonnegative"),
    )


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    source_id: Mapped[UUID] = mapped_column(
        ForeignKey("data_sources.id", ondelete="RESTRICT")
    )
    status: Mapped[str] = mapped_column(String(16), default="queued")
    payload: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    row_count: Mapped[int] = mapped_column(Integer)
    imported_count: Mapped[int] = mapped_column(Integer, default=0)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed')",
            name="ck_ingestion_jobs_status",
        ),
        CheckConstraint(
            "row_count > 0 AND imported_count >= 0 AND attempts >= 0",
            name="ck_ingestion_jobs_counts",
        ),
        Index("ix_ingestion_jobs_status_created", "status", "created_at"),
    )


class WarehouseLoad(Base):
    __tablename__ = "warehouse_loads"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    transformation_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("transformation_runs.id", ondelete="CASCADE"), unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(16), default="running")
    records_received: Mapped[int] = mapped_column(Integer, default=0)
    records_loaded: Mapped[int] = mapped_column(Integer, default=0)
    records_skipped: Mapped[int] = mapped_column(Integer, default=0)
    error_details: Mapped[str | None] = mapped_column(String(500))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    transformation_run: Mapped[TransformationRun] = relationship()

    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'succeeded', 'failed', 'warning')",
            name="ck_warehouse_loads_status",
        ),
        CheckConstraint(
            "records_received >= 0 AND records_loaded >= 0 AND records_skipped >= 0",
            name="ck_warehouse_loads_counts",
        ),
    )


class DimBeneficiary(Base):
    __tablename__ = "dim_beneficiary"

    beneficiary_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    beneficiary_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    gender: Mapped[str | None] = mapped_column(String(32))
    age_group: Mapped[str | None] = mapped_column(String(32))
    province: Mapped[str | None] = mapped_column(String(80))
    registration_date: Mapped[date | None] = mapped_column(Date)


class DimProgramme(Base):
    __tablename__ = "dim_programme"

    programme_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    programme_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    programme_name: Mapped[str] = mapped_column(String(120))
    programme_category: Mapped[str | None] = mapped_column(String(80))
    programme_status: Mapped[str | None] = mapped_column(String(16))


class DimLocation(Base):
    __tablename__ = "dim_location"

    location_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    province: Mapped[str] = mapped_column(String(80))
    district: Mapped[str | None] = mapped_column(String(120))
    municipality: Mapped[str | None] = mapped_column(String(120))
    location_name: Mapped[str | None] = mapped_column(String(120))

    __table_args__ = (
        Index(
            "uq_dim_location_natural",
            "province",
            "district",
            "municipality",
            "location_name",
            unique=True,
        ),
    )


class DimDate(Base):
    __tablename__ = "dim_date"

    date_key: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    day: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    month_name: Mapped[str] = mapped_column(String(20))
    quarter: Mapped[int] = mapped_column(Integer)
    year: Mapped[int] = mapped_column(Integer)


class DimOrganisation(Base):
    __tablename__ = "dim_organisation"

    organisation_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organisation_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    organisation_name: Mapped[str] = mapped_column(String(120))
    organisation_type: Mapped[str | None] = mapped_column(String(80))


class DimIndicator(Base):
    __tablename__ = "dim_indicator"

    indicator_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    indicator_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    indicator_name: Mapped[str] = mapped_column(String(160))
    indicator_category: Mapped[str | None] = mapped_column(String(80))
    measurement_unit: Mapped[str | None] = mapped_column(String(40))
    description: Mapped[str | None] = mapped_column(String(500))


class FactBeneficiaryParticipation(Base):
    __tablename__ = "fact_beneficiary_participation"

    participation_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    beneficiary_key: Mapped[int] = mapped_column(
        ForeignKey("dim_beneficiary.beneficiary_key"), index=True
    )
    programme_key: Mapped[int] = mapped_column(
        ForeignKey("dim_programme.programme_key"), index=True
    )
    location_key: Mapped[int] = mapped_column(
        ForeignKey("dim_location.location_key"), index=True
    )
    date_key: Mapped[int] = mapped_column(ForeignKey("dim_date.date_key"), index=True)
    participation_count: Mapped[int] = mapped_column(Integer, default=1)
    attendance_status: Mapped[str | None] = mapped_column(String(32))

    __table_args__ = (
        Index(
            "uq_fact_participation_grain",
            "beneficiary_key",
            "programme_key",
            "location_key",
            "date_key",
            unique=True,
        ),
    )


class FactProgrammeOutcome(Base):
    __tablename__ = "fact_programme_outcomes"

    outcome_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    programme_key: Mapped[int] = mapped_column(
        ForeignKey("dim_programme.programme_key"), index=True
    )
    location_key: Mapped[int] = mapped_column(
        ForeignKey("dim_location.location_key"), index=True
    )
    indicator_key: Mapped[int] = mapped_column(
        ForeignKey("dim_indicator.indicator_key"), index=True
    )
    date_key: Mapped[int] = mapped_column(ForeignKey("dim_date.date_key"), index=True)
    baseline_value: Mapped[float | None] = mapped_column()
    target_value: Mapped[float | None] = mapped_column()
    actual_value: Mapped[float | None] = mapped_column()
    achievement_percentage: Mapped[float | None] = mapped_column()

    __table_args__ = (
        Index(
            "uq_fact_programme_outcome_grain",
            "programme_key",
            "location_key",
            "indicator_key",
            "date_key",
            unique=True,
        ),
    )


class FactExpenditure(Base):
    __tablename__ = "fact_expenditure"

    expenditure_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    programme_key: Mapped[int] = mapped_column(ForeignKey("dim_programme.programme_key"))
    organisation_key: Mapped[int] = mapped_column(ForeignKey("dim_organisation.organisation_key"))
    location_key: Mapped[int] = mapped_column(ForeignKey("dim_location.location_key"))
    date_key: Mapped[int] = mapped_column(ForeignKey("dim_date.date_key"))
    budget_amount: Mapped[float | None] = mapped_column()
    actual_expenditure: Mapped[float | None] = mapped_column()
    remaining_budget: Mapped[float | None] = mapped_column()


class FactAssessment(Base):
    __tablename__ = "fact_assessments"

    assessment_key: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    beneficiary_key: Mapped[int] = mapped_column(ForeignKey("dim_beneficiary.beneficiary_key"))
    programme_key: Mapped[int] = mapped_column(ForeignKey("dim_programme.programme_key"))
    indicator_key: Mapped[int] = mapped_column(ForeignKey("dim_indicator.indicator_key"))
    date_key: Mapped[int] = mapped_column(ForeignKey("dim_date.date_key"))
    assessment_score: Mapped[float | None] = mapped_column()
    assessment_type: Mapped[str | None] = mapped_column(String(80))
