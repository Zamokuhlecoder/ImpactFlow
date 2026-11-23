from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrchestrationRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    airflow_dag_id: str
    airflow_run_id: str
    pipeline_run_id: UUID | None
    dataset_import_id: UUID | None
    status: str
    trigger_type: str
    execution_date: datetime
    started_at: datetime | None
    completed_at: datetime | None
    records_processed: int
    records_accepted: int
    records_rejected: int
    retry_count: int
    error_details: str | None


class OrchestrationDagRead(BaseModel):
    dag_id: str
    description: str | None
    schedule: str | None
    is_paused: bool
    last_run: dict[str, Any] | None = None


class OrchestrationRunSummaryRead(BaseModel):
    total_dags: int
    active_dags: int
    running_runs: int
    successful_runs: int
    failed_runs: int
    scheduled_runs: int
    available: bool
    message: str | None = None


class TriggerDagRequest(BaseModel):
    dataset_import_id: UUID | None = None
    conf: dict[str, Any] = Field(default_factory=dict)


class TriggerDagResponse(BaseModel):
    orchestration_run: OrchestrationRunRead
    airflow_run: dict[str, Any]


class TaskHistoryRead(BaseModel):
    task_id: str
    state: str | None
    start_date: datetime | None
    end_date: datetime | None
    duration: float | None
    try_number: int
    operator: str | None
