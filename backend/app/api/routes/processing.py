import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.database.session import get_db_session
from app.etl import transform_records
from app.models import (
    DataQualitySnapshot,
    Dataset,
    DatasetImport,
    PipelineRun,
    Programme,
    TransformationRun,
)
from app.phase3_ingestion import read_raw_dataset
from app.schemas.processing import (
    LayerDataRead,
    LayerDatasetRead,
    LayerName,
    ProcessingDatasetRead,
    ProcessingPipelineRead,
    TransformationRunCreate,
    TransformationRunRead,
)

logger = logging.getLogger("impactflow.processing")
router = APIRouter(prefix="/processing", tags=["ETL processing"])
DbSession = Annotated[Session, Depends(get_db_session)]
PIPELINE_NAME = "standardize_validate"
FILE_TYPES: dict[str, Literal["csv", "xlsx", "xls", "json"]] = {
    "csv": "csv",
    "json": "json",
    "rest api": "json",
    "postgresql": "json",
}


def _file_type(source_type: str, content: bytes) -> Literal["csv", "xlsx", "xls", "json"]:
    normalized = source_type.strip().casefold()
    if normalized == "excel":
        return "xlsx" if content.startswith(b"PK") else "xls"
    file_type = FILE_TYPES.get(normalized)
    if file_type is None:
        raise ValueError("This source type is not supported by the processing engine.")
    return file_type


def _write_json(directory: Path, filename: str, value: object) -> str:
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination = directory / filename
    temporary = destination.with_suffix(".tmp")
    with temporary.open("x", encoding="utf-8") as file:
        json.dump(
            value,
            file,
            ensure_ascii=False,
            allow_nan=False,
            default=lambda item: item.item() if hasattr(item, "item") else str(item),
        )
    temporary.replace(destination)
    return filename


def _read_json(directory: Path, filename: str) -> list[dict[str, object]]:
    try:
        value = json.loads((directory / filename).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        logger.error(
            "Processing artifact %s could not be read (%s).",
            filename,
            type(error).__name__,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="A processed data layer is unavailable.",
        ) from None
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="A processed data layer is invalid.",
        )
    return value


@router.get("/pipelines", response_model=list[ProcessingPipelineRead])
def list_processing_pipelines() -> list[ProcessingPipelineRead]:
    return [
        ProcessingPipelineRead(
            name=PIPELINE_NAME,
            label="Standardise, validate and aggregate",
            description=(
                "Clean categories and types, quarantine invalid or duplicate rows, "
                "and build Gold summaries."
            ),
        )
    ]


@router.get("/datasets", response_model=list[ProcessingDatasetRead])
def list_processing_datasets(session: DbSession) -> list[ProcessingDatasetRead]:
    imports = list(
        session.scalars(
            select(DatasetImport)
            .where(DatasetImport.raw_path.is_not(None))
            .order_by(DatasetImport.created_at.desc())
            .limit(100)
        )
    )
    import_ids = [entry.id for entry in imports]
    latest_runs: dict[UUID, TransformationRun] = {}
    if import_ids:
        runs = session.scalars(
            select(TransformationRun)
            .where(TransformationRun.dataset_import_id.in_(import_ids))
            .order_by(TransformationRun.started_at.desc())
        )
        for run in runs:
            latest_runs.setdefault(run.dataset_import_id, run)
    return [
        ProcessingDatasetRead(
            import_id=entry.id,
            dataset_id=entry.dataset_id,
            dataset_name=entry.dataset_name,
            source_name=entry.source_name,
            schema_type=entry.schema_type,
            import_status=entry.status,
            records_received=entry.records_received,
            imported_at=entry.created_at,
            can_process=bool(entry.raw_path),
            latest_run=latest_runs.get(entry.id),
        )
        for entry in imports
    ]


@router.post(
    "/runs",
    response_model=TransformationRunRead,
    status_code=status.HTTP_201_CREATED,
)
def run_processing_pipeline(
    payload: TransformationRunCreate,
    request: Request,
    session: DbSession,
) -> TransformationRun:
    settings: Settings = request.app.state.settings
    entry = session.get(DatasetImport, payload.dataset_import_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Dataset import not found.")
    if not entry.raw_path:
        raise HTTPException(status_code=409, detail="This import has no Bronze file to process.")
    run = TransformationRun(
        dataset_import_id=entry.id,
        dataset_id=entry.dataset_id,
        pipeline_name=payload.pipeline_name,
        schema_type=entry.schema_type,
        status="running",
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    created_files: list[Path] = []
    try:
        content = (settings.bronze_dir / entry.raw_path).read_bytes()
        rows = read_raw_dataset(content, _file_type(entry.source_type, content))
        known_programmes = None
        if entry.schema_type == "participation":
            known_programmes = {
                name.casefold() for name in session.scalars(select(Programme.name))
            }
        result = transform_records(rows, entry.schema_type, known_programmes)

        dataset = session.get(Dataset, entry.dataset_id) if entry.dataset_id else None
        if dataset is None:
            dataset = session.scalar(select(Dataset).where(Dataset.name == entry.dataset_name))
        if dataset is not None and dataset.source_id != entry.source_id:
            raise ValueError("The dataset name is already assigned to another source.")
        if dataset is None:
            dataset = Dataset(name=entry.dataset_name, source_id=entry.source_id)
            session.add(dataset)
            session.flush()

        run_id = str(run.id)
        run.silver_path = _write_json(
            settings.silver_dir, f"{run_id}.json", result["silver"]
        )
        created_files.append(settings.silver_dir / run.silver_path)
        run.quarantine_path = _write_json(
            settings.quarantine_dir, f"{run_id}.json", result["quarantine"]
        )
        created_files.append(settings.quarantine_dir / run.quarantine_path)
        gold_files: dict[str, str] = {}
        for name, records in result["gold"].items():
            filename = f"{run_id}_{name}.json"
            gold_files[name] = _write_json(settings.gold_dir, filename, records)
            created_files.append(settings.gold_dir / filename)

        report = result["quality_report"]
        run.dataset_id = dataset.id
        entry.dataset_id = dataset.id
        run.records_received = len(rows)
        run.records_processed = len(result["silver"])
        run.records_rejected = result["records_rejected"]
        run.duplicate_records = report["duplicate_records"]
        run.missing_values = report["missing_values"]
        run.quality_score = result["quality_score"]
        run.quality_report = report
        run.gold_files = gold_files
        run.status = "warning" if run.records_rejected else "succeeded"
        run.completed_at = datetime.now(UTC)
        session.add(
            PipelineRun(
                pipeline_name="ETL standardisation and validation",
                source_id=entry.source_id,
                status=run.status,
                records_processed=run.records_processed,
                started_at=run.started_at,
                completed_at=run.completed_at,
            )
        )
        session.add(DataQualitySnapshot(score=run.quality_score, checked_at=run.completed_at))
        session.commit()
    except (OSError, TypeError, ValueError, SQLAlchemyError) as error:
        session.rollback()
        for path in created_files:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                logger.error("Could not remove incomplete processing artifact %s.", path.name)
        run = session.get(TransformationRun, run.id)
        if run is None:
            raise HTTPException(
                status_code=503,
                detail="Processing history could not be updated.",
            ) from None
        detail = str(error) if isinstance(error, ValueError) else (
            "Layer storage operation failed."
            if isinstance(error, OSError)
            else "Database or transformation operation failed."
        )
        logger.error("Transformation %s failed (%s).", run.id, type(error).__name__)
        run.status = "failed"
        run.error_details = detail[:500]
        run.completed_at = datetime.now(UTC)
        session.add(
            PipelineRun(
                pipeline_name="ETL standardisation and validation",
                source_id=entry.source_id,
                status="failed",
                records_processed=run.records_processed,
                started_at=run.started_at,
                completed_at=run.completed_at,
            )
        )
        session.commit()
    session.refresh(run)
    return run


@router.get("/runs", response_model=list[TransformationRunRead])
def list_transformation_runs(
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[TransformationRun]:
    return list(
        session.scalars(
            select(TransformationRun)
            .order_by(TransformationRun.started_at.desc())
            .limit(limit)
        )
    )


@router.get("/datasets/{import_id}/layers/{layer}", response_model=LayerDataRead)
def read_processing_layer(
    import_id: UUID,
    layer: LayerName,
    request: Request,
    session: DbSession,
) -> LayerDataRead:
    settings: Settings = request.app.state.settings
    entry = session.get(DatasetImport, import_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Dataset import not found.")
    if layer == "bronze":
        if not entry.raw_path:
            return LayerDataRead(layer=layer, datasets=[])
        try:
            content = (settings.bronze_dir / entry.raw_path).read_bytes()
            rows = read_raw_dataset(content, _file_type(entry.source_type, content))
        except (OSError, ValueError) as error:
            logger.error(
                "Bronze dataset %s could not be read (%s).",
                import_id,
                type(error).__name__,
            )
            raise HTTPException(
                status_code=503,
                detail="The original Bronze dataset is unavailable or invalid.",
            ) from None
        return LayerDataRead(
            layer=layer,
            datasets=[LayerDatasetRead(name="Bronze · original rows", records=rows)],
        )

    run = session.scalar(
        select(TransformationRun)
        .where(
            TransformationRun.dataset_import_id == import_id,
            TransformationRun.status.in_(("succeeded", "warning")),
        )
        .order_by(TransformationRun.started_at.desc())
        .limit(1)
    )
    if run is None:
        return LayerDataRead(layer=layer, datasets=[])
    if layer == "silver":
        records = _read_json(settings.silver_dir, run.silver_path) if run.silver_path else []
        return LayerDataRead(
            layer=layer,
            datasets=[LayerDatasetRead(name="Silver · validated rows", records=records)],
        )
    if layer == "quarantine":
        records = (
            _read_json(settings.quarantine_dir, run.quarantine_path)
            if run.quarantine_path
            else []
        )
        return LayerDataRead(
            layer=layer,
            datasets=[LayerDatasetRead(name="Rejected · quarantined rows", records=records)],
        )
    return LayerDataRead(
        layer=layer,
        datasets=[
            LayerDatasetRead(
                name=name.replace("_", " ").title(),
                records=_read_json(settings.gold_dir, filename),
            )
            for name, filename in (run.gold_files or {}).items()
        ],
    )
