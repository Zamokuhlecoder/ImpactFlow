import argparse
import logging
import time
from datetime import UTC, datetime, timedelta
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.database.session import create_database_engine
from app.models import (
    DataSource,
    IngestionJob,
    IngestionRecord,
    PipelineRun,
    Programme,
)
from app.schemas.domain import ProgrammeInput

logger = logging.getLogger("impactflow.worker")
MAX_ATTEMPTS = 3
STALE_JOB_AGE = timedelta(minutes=15)
SessionFactory = sessionmaker[Session]


def recover_stale_jobs(session_factory: SessionFactory) -> None:
    now = datetime.now(UTC)
    stale_before = now - STALE_JOB_AGE
    with session_factory() as session:
        session.execute(
            update(IngestionJob)
            .where(
                IngestionJob.status == "running",
                IngestionJob.updated_at < stale_before,
                IngestionJob.attempts < MAX_ATTEMPTS,
            )
            .values(status="queued", error_code="worker_restarted", updated_at=now)
        )
        session.execute(
            update(IngestionJob)
            .where(
                IngestionJob.status == "running",
                IngestionJob.updated_at < stale_before,
                IngestionJob.attempts >= MAX_ATTEMPTS,
            )
            .values(
                status="failed",
                error_code="max_attempts_exceeded",
                completed_at=now,
                updated_at=now,
            )
        )
        session.commit()


def _claim_job(session_factory: SessionFactory) -> UUID | None:
    with session_factory() as session:
        job = session.scalar(
            select(IngestionJob)
            .where(IngestionJob.status == "queued")
            .order_by(IngestionJob.created_at, IngestionJob.id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if job is None:
            return None
        job.status = "running"
        job.started_at = datetime.now(UTC)
        job.attempts += 1
        job.error_code = None
        session.commit()
        return job.id


def _process_claimed_job(session_factory: SessionFactory, job_id: UUID) -> None:
    with session_factory() as session:
        job = session.get(IngestionJob, job_id)
        if job is None or job.status != "running":
            raise ValueError("Claimed ingestion job is no longer available.")
        source = session.get(DataSource, job.source_id)
        if (
            source is None
            or source.status != "active"
            or source.source_type.strip().casefold() != "csv"
        ):
            raise ValueError("Ingestion job no longer has an active CSV source.")

        for row in job.payload:
            try:
                programme_input = ProgrammeInput.model_validate(row)
            except ValidationError:
                raise ValueError("Stored CSV payload failed validation.") from None
            values = programme_input.model_dump()
            programme = session.scalar(
                select(Programme).where(Programme.name == programme_input.name)
            )
            if programme is None:
                session.add(Programme(**values))
            else:
                for field, value in values.items():
                    setattr(programme, field, value)

        now = datetime.now(UTC)
        source.records_count += job.row_count
        source.last_synced_at = now
        job.status = "succeeded"
        job.imported_count = job.row_count
        job.completed_at = now
        session.add(
            PipelineRun(
                pipeline_name="CSV programme import",
                source_id=source.id,
                status="succeeded",
                records_processed=job.row_count,
                started_at=job.started_at or now,
                completed_at=now,
            )
        )
        session.add(
            IngestionRecord(
                source_id=source.id,
                records_ingested=job.row_count,
                ingested_at=now,
            )
        )
        session.commit()


def _mark_failed(session_factory: SessionFactory, job_id: UUID, error_code: str) -> None:
    with session_factory() as session:
        job = session.get(IngestionJob, job_id)
        if job is not None and job.status == "running":
            job.status = "failed"
            job.error_code = error_code
            job.completed_at = datetime.now(UTC)
            session.commit()


def process_next_job(session_factory: SessionFactory) -> bool:
    job_id = _claim_job(session_factory)
    if job_id is None:
        return False
    try:
        _process_claimed_job(session_factory, job_id)
    except SQLAlchemyError as error:
        logger.error("Ingestion job %s failed (%s).", job_id, type(error).__name__)
        _mark_failed(session_factory, job_id, "database_write_failed")
    except ValueError as error:
        logger.error("Ingestion job %s failed validation (%s).", job_id, error)
        _mark_failed(session_factory, job_id, "invalid_job_payload")
    else:
        logger.info("Ingestion job %s succeeded.", job_id)
    return True


def _positive_seconds(value: str) -> float:
    seconds = float(value)
    if seconds <= 0:
        raise argparse.ArgumentTypeError("poll interval must be greater than zero.")
    return seconds


def main() -> None:
    parser = argparse.ArgumentParser(description="ImpactFlow database-backed ingestion worker")
    parser.add_argument("--once", action="store_true", help="Process at most one queued job.")
    parser.add_argument("--poll-seconds", type=_positive_seconds, default=2.0)
    args = parser.parse_args()

    settings = Settings()
    if not settings.database_url:
        raise SystemExit("Set IMPACTFLOW_DATABASE_URL before starting the worker.")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    engine = create_database_engine(settings.database_url)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    try:
        recover_stale_jobs(session_factory)
        if args.once:
            process_next_job(session_factory)
            return
        logger.info("Ingestion worker started.")
        while True:
            if not process_next_job(session_factory):
                time.sleep(args.poll_seconds)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
