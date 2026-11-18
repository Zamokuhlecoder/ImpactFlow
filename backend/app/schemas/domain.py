from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

Province = Literal[
    "Eastern Cape",
    "Free State",
    "Gauteng",
    "KwaZulu-Natal",
    "Limpopo",
    "Mpumalanga",
    "Northern Cape",
    "North West",
    "Western Cape",
]


class OrganisationInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class OrganisationRead(OrganisationInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class OrganisationUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class LocationInput(BaseModel):
    province: Province
    district: str | None = Field(default=None, min_length=1, max_length=120)
    area: str | None = Field(default=None, min_length=1, max_length=120)


class LocationRead(LocationInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


class LocationUpdate(BaseModel):
    province: Province | None = None
    district: str | None = Field(default=None, min_length=1, max_length=120)
    area: str | None = Field(default=None, min_length=1, max_length=120)

    @model_validator(mode="after")
    def require_update_fields(self) -> "LocationUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        if "province" in self.model_fields_set and self.province is None:
            raise ValueError("Province cannot be null.")
        return self


class DatasetInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    source_id: UUID | None = None


class DatasetRead(DatasetInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class DatasetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    source_id: UUID | None = None

    @model_validator(mode="after")
    def require_update_fields(self) -> "DatasetUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Name cannot be null.")
        return self


class ProgrammeInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=80)
    province: Province
    target_beneficiaries: int = Field(ge=0)
    reached_beneficiaries: int = Field(ge=0)
    status: Literal["active", "inactive"] = "active"


class ProgrammeRead(ProgrammeInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class ProgrammeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    category: str | None = Field(default=None, min_length=1, max_length=80)
    province: Province | None = None
    target_beneficiaries: int | None = Field(default=None, ge=0)
    reached_beneficiaries: int | None = Field(default=None, ge=0)
    status: Literal["active", "inactive"] | None = None

    @model_validator(mode="after")
    def require_update_fields(self) -> "ProgrammeUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        if any(value is None for value in self.model_dump(exclude_unset=True).values()):
            raise ValueError("Update fields cannot be null.")
        return self


class DataSourceInput(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    source_type: str = Field(min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    connection_ref: str | None = Field(
        default=None, min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$"
    )
    status: Literal["active", "inactive", "error"] = "active"
    records_count: int = Field(default=0, ge=0)
    last_synced_at: datetime | None = None


class DataSourceRead(DataSourceInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime


class DataSourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    source_type: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=500)
    connection_ref: str | None = Field(
        default=None, min_length=1, max_length=80, pattern=r"^[A-Za-z0-9_-]+$"
    )
    status: Literal["active", "inactive", "error"] | None = None
    records_count: int | None = Field(default=None, ge=0)
    last_synced_at: datetime | None = None

    @model_validator(mode="after")
    def require_update_fields(self) -> "DataSourceUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        if any(
            value is None and field not in {"last_synced_at", "description", "connection_ref"}
            for field, value in self.model_dump(exclude_unset=True).items()
        ):
            raise ValueError("Update fields cannot be null.")
        return self


class PipelineRunInput(BaseModel):
    pipeline_name: str = Field(min_length=1, max_length=120)
    source_id: UUID | None = None
    status: Literal["succeeded", "running", "failed", "warning"]
    records_processed: int = Field(default=0, ge=0)
    started_at: datetime | None = None
    completed_at: datetime | None = None


class PipelineRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pipeline_name: str
    source_id: UUID | None
    status: str
    records_processed: int
    started_at: datetime
    completed_at: datetime | None


class QualitySnapshotInput(BaseModel):
    score: float = Field(ge=0, le=100)
    checked_at: datetime | None = None


class QualitySnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    score: float
    checked_at: datetime


class IngestionRecordInput(BaseModel):
    source_id: UUID | None = None
    records_ingested: int = Field(ge=0)
    ingested_at: datetime | None = None


class IngestionRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID | None
    records_ingested: int
    ingested_at: datetime


class DashboardSummary(BaseModel):
    total_records: int
    total_sources: int
    active_sources: int
    successful_pipelines: int
    quality_score: float
    beneficiaries: int
    total_programmes: int
    active_programmes: int


class ProgrammePerformance(BaseModel):
    programme: str
    achievement: float
    target: int = 100


class ProvincialReach(BaseModel):
    province: str
    beneficiaries: int


class UserRead(BaseModel):
    id: UUID
    email: str
    role: Literal["admin", "viewer"]
    is_active: bool


class TrendPoint(BaseModel):
    day: str
    records: int


class PipelineTrendPoint(BaseModel):
    day: str
    succeeded: int
    running: int
    warning: int
    failed: int


class PipelineStatusCount(BaseModel):
    name: Literal["Succeeded", "Running", "Warning", "Failed"]
    value: int
    color: str


class QualityTrendPoint(BaseModel):
    day: str
    score: float


class DashboardExecution(BaseModel):
    id: UUID
    name: str
    source: str
    executed_at: datetime
    records: int
    duration: str
    duration_seconds: int
    status: Literal["Succeeded", "Running", "Warning", "Failed"]


class DashboardActivity(BaseModel):
    id: str
    title: str
    detail: str
    time: str
    tone: Literal["success", "warning", "info"]


class DashboardChanges(BaseModel):
    total_records: float | None
    active_sources: float | None
    successful_pipelines: float | None
    quality_score: float | None
    beneficiaries: float | None
    active_programmes: float | None


class DashboardSnapshot(BaseModel):
    has_data: bool
    metrics: DashboardSummary
    changes: DashboardChanges
    ingestion_trend: list[TrendPoint]
    pipeline_runs: list[PipelineTrendPoint]
    pipeline_status: list[PipelineStatusCount]
    programme_performance: list[ProgrammePerformance]
    quality_trend: list[QualityTrendPoint]
    provincial_reach: list[ProvincialReach]
    executions: list[DashboardExecution]
    activities: list[DashboardActivity]
