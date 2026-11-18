from http import HTTPStatus
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.ingestion import MAX_CSV_BYTES, parse_programme_csv
from app.models import DataSource, IngestionJob
from app.schemas.ingestion import IngestionJobRead

router = APIRouter(
    prefix="/ingestions",
    tags=["ingestion jobs"],
)
DbSession = Annotated[Session, Depends(get_db_session)]


@router.post(
    "/csv",
    response_model=IngestionJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def enqueue_programme_csv(
    session: DbSession,
    source_id: Annotated[UUID, Form()],
    file: Annotated[UploadFile, File()],
) -> IngestionJob:
    if not file.filename or not file.filename.casefold().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Upload a .csv file.",
        )
    content = file.file.read(MAX_CSV_BYTES + 1)
    try:
        rows = parse_programme_csv(content)
    except ValueError as error:
        raise HTTPException(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from None

    source = session.get(DataSource, source_id)
    if source is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found.")
    if source.status != "active" or source.source_type.strip().casefold() != "csv":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Select an active data source with type CSV.",
        )

    job = IngestionJob(source_id=source.id, payload=rows, row_count=len(rows))
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


@router.get("/jobs", response_model=list[IngestionJobRead])
def list_ingestion_jobs(
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[IngestionJob]:
    return list(
        session.scalars(
            select(IngestionJob)
            .order_by(IngestionJob.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    )


@router.get("/jobs/{job_id}", response_model=IngestionJobRead)
def get_ingestion_job(job_id: UUID, session: DbSession) -> IngestionJob:
    job = session.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ingestion job not found.",
        )
    return job
