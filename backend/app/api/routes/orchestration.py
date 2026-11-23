import hmac
from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.session import get_db_session
from app.models import OrchestrationRun
from app.orchestration import AirflowClient, OrchestrationUnavailable
from app.schemas.orchestration import (
    OrchestrationDagRead,
    OrchestrationRunRead,
    OrchestrationRunSummaryRead,
    TaskHistoryRead,
    TriggerDagRequest,
    TriggerDagResponse,
)

router = APIRouter(prefix="/orchestration", tags=["orchestration"])
DbSession = Annotated[Session, Depends(get_db_session)]


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _client(request: Request) -> AirflowClient:
    try:
        return AirflowClient(_settings(request))
    except OrchestrationUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from None


def _protect(
    request: Request,
    token: Annotated[str | None, Header(alias="X-Orchestration-Token")] = None,
) -> None:
    configured = _settings(request).orchestration_token
    if configured and not token:
        raise HTTPException(status_code=401, detail="An orchestration token is required.")
    if configured and not hmac.compare_digest(token or "", configured.get_secret_value()):
        raise HTTPException(status_code=403, detail="The orchestration token is invalid.")


Protection = Annotated[None, Depends(_protect)]


def _status(value: object) -> str:
    return {
        "queued": "queued",
        "scheduled": "queued",
        "running": "running",
        "success": "success",
        "failed": "failed",
        "up_for_retry": "up_for_retry",
        "up_for_reschedule": "running",
        "cancelled": "cancelled",
    }.get(str(value), "queued")


def _parse_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


@router.get("/dags", response_model=list[OrchestrationDagRead])
def list_dags(request: Request, _protected: Protection) -> list[OrchestrationDagRead]:
    client = _client(request)
    try:
        dags = client.dags()
    except OrchestrationUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
    return [
        OrchestrationDagRead(
            dag_id=str(dag.get("dag_id", "")),
            description=dag.get("description"),
            schedule=dag.get("timetable_summary") or dag.get("schedule_interval"),
            is_paused=bool(dag.get("is_paused", False)),
        )
        for dag in dags
        if dag.get("dag_id")
    ]


@router.get("/runs", response_model=list[OrchestrationRunRead])
def list_runs(
    request: Request,
    session: DbSession,
    _protected: Protection,
    dag_id: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[OrchestrationRun]:
    client = _client(request)
    try:
        if dag_id:
            airflow_runs = client.runs(dag_id)
        else:
            dags = client.dags()
            airflow_runs = [
                run
                for dag in dags
                for run in client.runs(str(dag["dag_id"]))
            ]
    except OrchestrationUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
    result: list[OrchestrationRun] = []
    for airflow_run in airflow_runs[:limit]:
        airflow_run_id = airflow_run.get("dag_run_id") or airflow_run.get("run_id")
        airflow_dag_id = airflow_run.get("dag_id")
        if not isinstance(airflow_run_id, str) or not isinstance(airflow_dag_id, str):
            continue
        record = session.scalar(
            select(OrchestrationRun).where(
                OrchestrationRun.airflow_run_id == airflow_run_id
            )
        )
        if record is None:
            record = OrchestrationRun(
                id=uuid4(),
                airflow_dag_id=airflow_dag_id,
                airflow_run_id=airflow_run_id,
                status=_status(airflow_run.get("state")),
                trigger_type="scheduled" if airflow_run_id.startswith("scheduled__") else "manual",
                execution_date=_parse_datetime(airflow_run.get("logical_date"))
                or datetime.now().astimezone(),
            )
            session.add(record)
        else:
            record.status = _status(airflow_run.get("state"))
        record.started_at = _parse_datetime(airflow_run.get("start_date"))
        record.completed_at = _parse_datetime(airflow_run.get("end_date"))
        result.append(record)
    session.commit()
    return result


@router.post(
    "/dags/{dag_id}/trigger",
    response_model=TriggerDagResponse,
    status_code=status.HTTP_201_CREATED,
)
def trigger_dag(
    dag_id: str,
    payload: TriggerDagRequest,
    request: Request,
    session: DbSession,
    _protected: Protection,
) -> TriggerDagResponse:
    if not dag_id.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(status_code=422, detail="Invalid DAG identifier.")
    client = _client(request)
    conf = dict(payload.conf)
    if payload.dataset_import_id:
        conf["dataset_import_id"] = str(payload.dataset_import_id)
    try:
        airflow_run = client.trigger(dag_id, conf)
    except OrchestrationUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
    airflow_run_id = airflow_run.get("dag_run_id") or airflow_run.get("run_id")
    if not isinstance(airflow_run_id, str):
        raise HTTPException(status_code=502, detail="Airflow did not return a run identifier.")
    record = OrchestrationRun(
        airflow_dag_id=dag_id,
        airflow_run_id=airflow_run_id,
        dataset_import_id=payload.dataset_import_id,
        status="queued",
        trigger_type="manual",
        execution_date=_parse_datetime(airflow_run.get("logical_date"))
        or datetime.now().astimezone(),
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return TriggerDagResponse(orchestration_run=record, airflow_run=airflow_run)


@router.get("/runs/{run_id}/tasks", response_model=list[TaskHistoryRead])
def task_history(
    run_id: UUID,
    request: Request,
    session: DbSession,
    _protected: Protection,
) -> list[TaskHistoryRead]:
    record = session.get(OrchestrationRun, run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Orchestration run not found.")
    client = _client(request)
    try:
        tasks = client.tasks(record.airflow_dag_id, record.airflow_run_id)
    except OrchestrationUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from None
    return [
        TaskHistoryRead(
            task_id=str(task.get("task_id", "")),
            state=task.get("state"),
            start_date=_parse_datetime(task.get("start_date")),
            end_date=_parse_datetime(task.get("end_date")),
            duration=task.get("duration"),
            try_number=int(task.get("try_number", 0)),
            operator=task.get("operator_name") or task.get("operator"),
        )
        for task in tasks
        if task.get("task_id")
    ]


@router.get("/monitoring/summary", response_model=OrchestrationRunSummaryRead)
def monitoring_summary(request: Request, _protected: Protection) -> OrchestrationRunSummaryRead:
    try:
        client = AirflowClient(_settings(request))
        dags = client.dags()
        runs = [
            run
            for dag in dags
            for run in client.runs(str(dag["dag_id"]))
        ]
    except OrchestrationUnavailable as error:
        return OrchestrationRunSummaryRead(
            total_dags=0,
            active_dags=0,
            running_runs=0,
            successful_runs=0,
            failed_runs=0,
            scheduled_runs=0,
            available=False,
            message=str(error),
        )
    states = [str(run.get("state")) for run in runs]
    return OrchestrationRunSummaryRead(
        total_dags=len(dags),
        active_dags=sum(not bool(dag.get("is_paused", False)) for dag in dags),
        running_runs=states.count("running"),
        successful_runs=states.count("success"),
        failed_runs=states.count("failed"),
        scheduled_runs=sum(
            str(run.get("run_id") or run.get("dag_run_id", "")).startswith("scheduled__")
            for run in runs
        ),
        available=True,
    )
