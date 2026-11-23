from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class WarehouseLoadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    transformation_run_id: UUID
    status: Literal["running", "succeeded", "failed", "warning"]
    records_received: int
    records_loaded: int
    records_skipped: int
    error_details: str | None
    started_at: datetime
    completed_at: datetime | None

class WarehouseOverviewRead(BaseModel):
    dimensions: dict[str, int]
    facts: dict[str, int]
    latest_load: WarehouseLoadRead | None
    supported_fields: list[str]
    unavailable_fields: list[str]


class ProgrammePerformanceRead(BaseModel):
    programme: str
    province: str
    target: float | None
    actual: float | None
    achievement_percentage: float | None


class ProvincialPerformanceRead(BaseModel):
    province: str
    programmes: int
    participants: int


class BeneficiaryParticipationRead(BaseModel):
    beneficiary_id: str
    programmes: int
    participation_records: int


class AnalyticsUnavailableRead(BaseModel):
    available: Literal[False] = False
    reason: str
