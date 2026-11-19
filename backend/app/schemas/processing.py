from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.phase3_ingestion import SchemaType

PipelineName = Literal["standardize_validate"]
LayerName = Literal["bronze", "silver", "gold", "quarantine"]


class TransformationRunCreate(BaseModel):
    dataset_import_id: UUID
    pipeline_name: PipelineName


class ProcessingPipelineRead(BaseModel):
    name: PipelineName
    label: str
    description: str


class QualityReportRead(BaseModel):
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    duplicate_records: int = 0
    missing_values: int = 0
    quality_percentage: float = 0


class TransformationRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    dataset_import_id: UUID
    dataset_id: UUID | None
    pipeline_name: str
    schema_type: SchemaType
    status: Literal["running", "succeeded", "failed", "warning"]
    records_received: int
    records_processed: int
    records_rejected: int
    duplicate_records: int
    missing_values: int
    quality_score: float
    quality_report: QualityReportRead
    error_details: str | None
    started_at: datetime
    completed_at: datetime | None


class ProcessingDatasetRead(BaseModel):
    import_id: UUID
    dataset_id: UUID | None
    dataset_name: str
    source_name: str
    schema_type: SchemaType
    import_status: Literal["running", "succeeded", "failed"]
    records_received: int
    imported_at: datetime
    can_process: bool
    latest_run: TransformationRunRead | None


class LayerDatasetRead(BaseModel):
    name: str
    records: list[dict[str, object]]


class LayerDataRead(BaseModel):
    layer: LayerName
    datasets: list[LayerDatasetRead]
