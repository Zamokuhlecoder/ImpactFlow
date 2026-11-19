from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.phase3_ingestion import SchemaType


class IngestionJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID
    status: Literal["queued", "running", "succeeded", "failed"]
    row_count: int
    imported_count: int
    attempts: int
    error_code: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class DatasetImportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID | None
    dataset_id: UUID | None
    source_name: str
    source_type: str
    dataset_name: str
    schema_type: SchemaType
    status: Literal["running", "succeeded", "failed"]
    records_received: int
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class ConnectionImportInput(BaseModel):
    source_id: UUID
    dataset_name: str = Field(min_length=1, max_length=120)
    schema_type: SchemaType
