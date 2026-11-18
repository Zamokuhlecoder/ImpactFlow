from datetime import UTC, datetime, time, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.models import (
    DataQualitySnapshot,
    DataSource,
    IngestionJob,
    IngestionRecord,
    PipelineRun,
    Programme,
)
from app.schemas.domain import (
    DashboardActivity,
    DashboardChanges,
    DashboardExecution,
    DashboardSnapshot,
    DashboardSummary,
    DataSourceInput,
    DataSourceRead,
    DataSourceUpdate,
    IngestionRecordInput,
    IngestionRecordRead,
    PipelineRunInput,
    PipelineRunRead,
    PipelineStatusCount,
    PipelineTrendPoint,
    ProgrammeInput,
    ProgrammePerformance,
    ProgrammeRead,
    ProgrammeUpdate,
    ProvincialReach,
    QualitySnapshotInput,
    QualitySnapshotRead,
    QualityTrendPoint,
    TrendPoint,
)

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db_session)]


def _commit_or_conflict(session: Session, message: str) -> None:
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=message,
        ) from None


def _relative_time(value: datetime, now: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    minutes = max(0, int((now - value.astimezone(UTC)).total_seconds() // 60))
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes} min ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = hours // 24
    return f"{days} day{'s' if days != 1 else ''} ago"


def _percent_change(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)


@router.get("/dashboard/snapshot", response_model=DashboardSnapshot, tags=["dashboard"])
def dashboard_snapshot(
    session: DbSession,
    days: Annotated[int, Query(ge=7, le=90)] = 30,
) -> DashboardSnapshot:
    now = datetime.now(UTC)
    today = now.date()
    period_start = datetime.combine(today - timedelta(days=days - 1), time.min, tzinfo=UTC)
    run_rows = list(
        session.scalars(
            select(PipelineRun)
            .where(PipelineRun.started_at >= period_start)
            .order_by(PipelineRun.started_at)
        )
    )
    ingestion_rows = list(
        session.scalars(
            select(IngestionRecord)
            .where(IngestionRecord.ingested_at >= period_start)
            .order_by(IngestionRecord.ingested_at)
        )
    )

    daily_runs = {
        today - timedelta(days=offset): {
            "succeeded": 0,
            "running": 0,
            "warning": 0,
            "failed": 0,
        }
        for offset in range(days - 1, -1, -1)
    }
    for run in run_rows:
        run_day = run.started_at.date()
        if run_day in daily_runs and run.status in daily_runs[run_day]:
            daily_runs[run_day][run.status] += 1

    daily_ingestion = {day: 0 for day in daily_runs}
    for record in ingestion_rows:
        record_day = record.ingested_at.date()
        if record_day in daily_ingestion:
            daily_ingestion[record_day] += record.records_ingested

    pipeline_runs = [
        PipelineTrendPoint(day=day.strftime("%d %b"), **counts)
        for day, counts in daily_runs.items()
    ]
    ingestion_trend = [
        TrendPoint(day=day.strftime("%d %b"), records=records)
        for day, records in daily_ingestion.items()
    ]
    pipeline_status = [
        PipelineStatusCount(name=name, value=count, color=color)
        for name, count, color in (
            ("Succeeded", sum(row["succeeded"] for row in daily_runs.values()), "#22C55E"),
            ("Running", sum(row["running"] for row in daily_runs.values()), "#FACC15"),
            ("Warning", sum(row["warning"] for row in daily_runs.values()), "#FACC15"),
            ("Failed", sum(row["failed"] for row in daily_runs.values()), "#F43F5E"),
        )
    ]

    total_records = session.scalar(select(func.coalesce(func.sum(DataSource.records_count), 0)))
    total_sources = session.scalar(select(func.count(DataSource.id))) or 0
    active_sources = session.scalar(
        select(func.count(DataSource.id)).where(DataSource.status == "active")
    )
    active_programmes = session.scalar(
        select(func.count(Programme.id)).where(Programme.status == "active")
    )
    total_programmes = session.scalar(select(func.count(Programme.id))) or 0
    beneficiaries = session.scalar(
        select(func.coalesce(func.sum(Programme.reached_beneficiaries), 0))
    )
    quality_rows = list(
        session.scalars(
            select(DataQualitySnapshot)
            .order_by(DataQualitySnapshot.checked_at.desc())
            .limit(12)
        )
    )
    quality_rows.reverse()
    quality_score = quality_rows[-1].score if quality_rows else 0
    quality_change = (
        _percent_change(quality_rows[-1].score, quality_rows[-2].score)
        if len(quality_rows) > 1
        else None
    )

    current_period_start = now - timedelta(days=30)
    previous_period_start = now - timedelta(days=60)
    current_successes = session.scalar(
        select(func.count(PipelineRun.id)).where(
            PipelineRun.status == "succeeded",
            PipelineRun.started_at >= current_period_start,
        )
    ) or 0
    previous_successes = session.scalar(
        select(func.count(PipelineRun.id)).where(
            PipelineRun.status == "succeeded",
            PipelineRun.started_at >= previous_period_start,
            PipelineRun.started_at < current_period_start,
        )
    ) or 0

    programme_rows = list(
        session.scalars(
            select(Programme).where(Programme.status == "active").order_by(Programme.name)
        )
    )
    programme_performance = [
        ProgrammePerformance(
            programme=programme.name,
            achievement=(
                round(
                    programme.reached_beneficiaries
                    / programme.target_beneficiaries
                    * 100,
                    1,
                )
                if programme.target_beneficiaries
                else 0
            ),
        )
        for programme in programme_rows
    ]
    provincial_rows = session.execute(
        select(
            Programme.province,
            func.sum(Programme.reached_beneficiaries).label("beneficiaries"),
        )
        .where(Programme.status == "active")
        .group_by(Programme.province)
        .order_by(Programme.province)
    )

    recent_runs = list(
        session.scalars(
            select(PipelineRun)
            .where(PipelineRun.started_at >= period_start)
            .order_by(PipelineRun.started_at.desc())
            .limit(8)
        )
    )
    executions = []
    for run in recent_runs:
        started = run.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=UTC)
        ended = run.completed_at or now
        if ended.tzinfo is None:
            ended = ended.replace(tzinfo=UTC)
        duration_seconds = max(0, int((ended - started).total_seconds()))
        minutes, seconds = divmod(duration_seconds, 60)
        executions.append(
            DashboardExecution(
                id=run.id,
                name=run.pipeline_name,
                source=run.source.name if run.source else "Unlinked source",
                executed_at=started,
                records=run.records_processed,
                duration=f"{minutes}m {seconds}s",
                duration_seconds=duration_seconds,
                status=run.status.title(),
            )
        )

    recent_ingestions = list(
        session.scalars(
            select(IngestionRecord)
            .where(IngestionRecord.ingested_at >= period_start)
            .order_by(IngestionRecord.ingested_at.desc())
            .limit(8)
        )
    )
    event_items: list[tuple[datetime, DashboardActivity]] = []
    for run in recent_runs:
        event_time = run.started_at
        tone = (
            "success"
            if run.status == "succeeded"
            else "warning"
            if run.status in {"failed", "warning"}
            else "info"
        )
        event_items.append(
            (
                event_time,
                DashboardActivity(
                    id=f"pipeline-{run.id}",
                    title=f"{run.pipeline_name} {run.status}",
                    detail=f"{run.records_processed:,} records processed",
                    time=_relative_time(event_time, now),
                    tone=tone,
                ),
            )
        )
    for record in recent_ingestions:
        event_items.append(
            (
                record.ingested_at,
                DashboardActivity(
                    id=f"ingestion-{record.id}",
                    title="Ingestion batch recorded",
                    detail=f"{record.records_ingested:,} records ingested",
                    time=_relative_time(record.ingested_at, now),
                    tone="info",
                ),
            )
        )
    activities = [
        activity for _, activity in sorted(event_items, key=lambda item: item[0], reverse=True)[:3]
    ]

    table_counts = [
        session.scalar(select(func.count()).select_from(table)) or 0
        for table in (
            Programme,
            DataSource,
            PipelineRun,
            DataQualitySnapshot,
            IngestionRecord,
            IngestionJob,
        )
    ]
    return DashboardSnapshot(
        has_data=any(table_counts),
        metrics=DashboardSummary(
            total_records=total_records or 0,
            total_sources=total_sources,
            active_sources=active_sources or 0,
            successful_pipelines=current_successes,
            quality_score=quality_score,
            beneficiaries=beneficiaries or 0,
            total_programmes=total_programmes,
            active_programmes=active_programmes or 0,
        ),
        changes=DashboardChanges(
            total_records=None,
            active_sources=None,
            successful_pipelines=_percent_change(current_successes, previous_successes),
            quality_score=quality_change,
            beneficiaries=None,
            active_programmes=None,
        ),
        ingestion_trend=ingestion_trend,
        pipeline_runs=pipeline_runs,
        pipeline_status=pipeline_status,
        programme_performance=programme_performance,
        quality_trend=[
            QualityTrendPoint(day=row.checked_at.strftime("%d %b"), score=row.score)
            for row in quality_rows
        ],
        provincial_reach=[
            ProvincialReach(province=province, beneficiaries=beneficiaries)
            for province, beneficiaries in provincial_rows
        ],
        executions=executions,
        activities=activities,
    )


@router.get("/dashboard/summary", response_model=DashboardSummary, tags=["dashboard"])
def dashboard_summary(session: DbSession) -> DashboardSummary:
    total_records = session.scalar(select(func.coalesce(func.sum(DataSource.records_count), 0)))
    total_sources = session.scalar(select(func.count(DataSource.id))) or 0
    active_sources = session.scalar(
        select(func.count(DataSource.id)).where(DataSource.status == "active")
    )
    successful_pipelines = session.scalar(
        select(func.count(PipelineRun.id)).where(PipelineRun.status == "succeeded")
    )
    quality_score = session.scalar(
        select(DataQualitySnapshot.score).order_by(DataQualitySnapshot.checked_at.desc()).limit(1)
    )
    beneficiaries = session.scalar(
        select(func.coalesce(func.sum(Programme.reached_beneficiaries), 0))
    )
    active_programmes = session.scalar(
        select(func.count(Programme.id)).where(Programme.status == "active")
    )
    total_programmes = session.scalar(select(func.count(Programme.id))) or 0
    return DashboardSummary(
        total_records=total_records or 0,
        total_sources=total_sources,
        active_sources=active_sources or 0,
        successful_pipelines=successful_pipelines or 0,
        quality_score=quality_score or 0,
        beneficiaries=beneficiaries or 0,
        total_programmes=total_programmes,
        active_programmes=active_programmes or 0,
    )


@router.get(
    "/dashboard/programme-performance",
    response_model=list[ProgrammePerformance],
    tags=["dashboard"],
)
def programme_performance(session: DbSession) -> list[ProgrammePerformance]:
    programmes = session.scalars(
        select(Programme).where(Programme.status == "active").order_by(Programme.name)
    )
    return [
        ProgrammePerformance(
            programme=programme.name,
            achievement=(
                round(programme.reached_beneficiaries / programme.target_beneficiaries * 100, 1)
                if programme.target_beneficiaries
                else 0
            ),
            target=programme.target_beneficiaries,
        )
        for programme in programmes
    ]


@router.get(
    "/dashboard/provincial-reach",
    response_model=list[ProvincialReach],
    tags=["dashboard"],
)
def provincial_reach(session: DbSession) -> list[ProvincialReach]:
    rows = session.execute(
        select(
            Programme.province,
            func.sum(Programme.reached_beneficiaries).label("beneficiaries"),
        )
        .where(Programme.status == "active")
        .group_by(Programme.province)
        .order_by(Programme.province)
    )
    return [
        ProvincialReach(province=province, beneficiaries=beneficiaries)
        for province, beneficiaries in rows
    ]


@router.get("/programmes", response_model=list[ProgrammeRead], tags=["programmes"])
def list_programmes(
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Programme]:
    return list(
        session.scalars(
            select(Programme).order_by(Programme.name).limit(limit).offset(offset)
        )
    )


@router.post(
    "/programmes",
    response_model=ProgrammeRead,
    status_code=status.HTTP_201_CREATED,
    tags=["programmes"],
)
def create_programme(
    payload: ProgrammeInput,
    session: DbSession,
) -> Programme:
    programme = Programme(**payload.model_dump())
    session.add(programme)
    _commit_or_conflict(session, "A programme with this name already exists.")
    session.refresh(programme)
    return programme


@router.patch("/programmes/{programme_id}", response_model=ProgrammeRead, tags=["programmes"])
def update_programme(
    programme_id: UUID,
    payload: ProgrammeUpdate,
    session: DbSession,
) -> Programme:
    programme = session.get(Programme, programme_id)
    if programme is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Programme not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(programme, field, value)
    _commit_or_conflict(session, "A programme with this name already exists.")
    session.refresh(programme)
    return programme


@router.delete(
    "/programmes/{programme_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["programmes"],
)
def delete_programme(programme_id: UUID, session: DbSession) -> None:
    programme = session.get(Programme, programme_id)
    if programme is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Programme not found.")
    session.delete(programme)
    session.commit()


@router.get("/data-sources", response_model=list[DataSourceRead], tags=["data sources"])
def list_data_sources(
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DataSource]:
    return list(
        session.scalars(
            select(DataSource).order_by(DataSource.name).limit(limit).offset(offset)
        )
    )


@router.post(
    "/data-sources",
    response_model=DataSourceRead,
    status_code=status.HTTP_201_CREATED,
    tags=["data sources"],
)
def create_data_source(payload: DataSourceInput, session: DbSession) -> DataSource:
    data_source = DataSource(**payload.model_dump())
    session.add(data_source)
    _commit_or_conflict(session, "A data source with this name already exists.")
    session.refresh(data_source)
    return data_source


@router.patch(
    "/data-sources/{source_id}", response_model=DataSourceRead, tags=["data sources"]
)
def update_data_source(
    source_id: UUID,
    payload: DataSourceUpdate,
    session: DbSession,
) -> DataSource:
    data_source = session.get(DataSource, source_id)
    if data_source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(data_source, field, value)
    _commit_or_conflict(session, "A data source with this name already exists.")
    session.refresh(data_source)
    return data_source


@router.delete(
    "/data-sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["data sources"],
)
def delete_data_source(source_id: UUID, session: DbSession) -> None:
    data_source = session.get(DataSource, source_id)
    if data_source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found.")
    session.delete(data_source)
    _commit_or_conflict(session, "This source has queued ingestion jobs and cannot be deleted.")


@router.get("/pipeline-runs", response_model=list[PipelineRunRead], tags=["pipeline runs"])
def list_pipeline_runs(
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[PipelineRun]:
    return list(
        session.scalars(
            select(PipelineRun)
            .order_by(PipelineRun.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )


@router.post(
    "/pipeline-runs",
    response_model=PipelineRunRead,
    status_code=status.HTTP_201_CREATED,
    tags=["pipeline runs"],
)
def record_pipeline_run(
    payload: PipelineRunInput,
    session: DbSession,
) -> PipelineRun:
    pipeline_run = PipelineRun(**payload.model_dump(exclude_none=True))
    session.add(pipeline_run)
    _commit_or_conflict(session, "Pipeline run references an unknown data source.")
    session.refresh(pipeline_run)
    return pipeline_run


@router.get(
    "/data-quality/snapshots",
    response_model=list[QualitySnapshotRead],
    tags=["data quality"],
)
def list_quality_snapshots(
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DataQualitySnapshot]:
    return list(
        session.scalars(
            select(DataQualitySnapshot)
            .order_by(DataQualitySnapshot.checked_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )


@router.post(
    "/data-quality/snapshots",
    response_model=QualitySnapshotRead,
    status_code=status.HTTP_201_CREATED,
    tags=["data quality"],
)
def create_quality_snapshot(
    payload: QualitySnapshotInput,
    session: DbSession,
) -> DataQualitySnapshot:
    snapshot = DataQualitySnapshot(**payload.model_dump(exclude_none=True))
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot


@router.get(
    "/ingestion-records",
    response_model=list[IngestionRecordRead],
    tags=["ingestion records"],
)
def list_ingestion_records(
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[IngestionRecord]:
    return list(
        session.scalars(
            select(IngestionRecord)
            .order_by(IngestionRecord.ingested_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )


@router.post(
    "/ingestion-records",
    response_model=IngestionRecordRead,
    status_code=status.HTTP_201_CREATED,
    tags=["ingestion records"],
)
def create_ingestion_record(
    payload: IngestionRecordInput,
    session: DbSession,
) -> IngestionRecord:
    record = IngestionRecord(**payload.model_dump(exclude_none=True))
    session.add(record)
    _commit_or_conflict(session, "Ingestion record references an unknown data source.")
    session.refresh(record)
    return record
