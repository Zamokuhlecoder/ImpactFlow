import logging
from collections.abc import Callable
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.connectors import ConnectorError, fetch_postgresql, fetch_rest
from app.core.config import Settings
from app.database.session import get_db_session
from app.ingestion import MAX_CSV_BYTES
from app.models import Dataset, DatasetImport, DataSource, IngestionRecord, Programme
from app.phase3_ingestion import SchemaType, parse_dataset
from app.schemas.ingestion import ConnectionImportInput, DatasetImportRead

logger = logging.getLogger("impactflow.imports")
router = APIRouter(prefix="/imports", tags=["dataset imports"])
DbSession = Annotated[Session, Depends(get_db_session)]
FILE_TYPES: dict[str, Literal["csv", "xlsx", "json"]] = {
    "csv": "csv",
    "excel": "xlsx",
    "json": "json",
}
CONNECTION_TYPES = {"rest api": "rest", "postgresql": "postgresql"}


@router.get("/connections")
def list_connections(request: Request) -> list[dict[str, str]]:
    settings: Settings = request.app.state.settings
    return [
        {"reference": reference, "kind": connection.kind}
        for reference, connection in settings.source_connections.items()
    ]


@router.post("/files", response_model=DatasetImportRead, status_code=201)
def import_file(
    request: Request,
    session: DbSession,
    source_id: Annotated[UUID, Form()],
    dataset_name: Annotated[str, Form(min_length=1, max_length=120)],
    schema_type: Annotated[SchemaType, Form()],
    file: Annotated[UploadFile, File()],
) -> DatasetImport:
    source = session.get(DataSource, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Data source not found.")
    source_type = source.source_type.strip().casefold()
    if source.status == "inactive" or source_type not in FILE_TYPES:
        raise HTTPException(status_code=409, detail="Select an enabled file data source.")
    expected: Literal["csv", "xlsx", "xls", "json"] = FILE_TYPES[source_type]
    suffix = Path(file.filename or "").suffix.casefold()
    if source_type == "excel" and suffix == ".xls":
        expected = "xls"

    def read_file() -> bytes:
        if not file.filename or Path(file.filename).suffix.casefold() != f".{expected}":
            raise ValueError(f"Select a .{expected} file for this source.")
        return file.file.read(MAX_CSV_BYTES + 1)

    settings: Settings = request.app.state.settings
    return _run_import(session, settings, source, dataset_name, schema_type, expected, read_file)


@router.post("/connections", response_model=DatasetImportRead, status_code=201)
def import_connection(
    payload: ConnectionImportInput, request: Request, session: DbSession
) -> DatasetImport:
    source = session.get(DataSource, payload.source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Data source not found.")
    source_type = source.source_type.strip().casefold()
    if source.status == "inactive" or source_type not in CONNECTION_TYPES:
        raise HTTPException(
            status_code=409, detail="Select an enabled REST API or PostgreSQL source."
        )
    settings: Settings = request.app.state.settings

    def read_connection() -> bytes:
        config = settings.source_connections.get(source.connection_ref or "")
        if config is None or config.kind != CONNECTION_TYPES[source_type]:
            raise ConnectorError("Source connection is not configured or has the wrong type.")
        return fetch_rest(config) if config.kind == "rest" else fetch_postgresql(config)

    return _run_import(
        session,
        settings,
        source,
        payload.dataset_name,
        payload.schema_type,
        "json",
        read_connection,
    )


def _run_import(
    session: Session,
    settings: Settings,
    source: DataSource,
    dataset_name: str,
    schema_type: SchemaType,
    file_type: Literal["csv", "xlsx", "xls", "json"],
    read_content: Callable[[], bytes],
) -> DatasetImport:
    name = dataset_name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Dataset name cannot be blank.")
    entry = DatasetImport(
        source_id=source.id,
        source_name=source.name,
        source_type=source.source_type,
        dataset_name=name,
        schema_type=schema_type,
        status="running",
        records_received=0,
    )
    session.add(entry)
    session.commit()

    try:
        content = read_content()
        if len(content) > MAX_CSV_BYTES:
            raise ValueError("The file exceeds the 2 MB limit.")
        settings.bronze_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        raw_path = f"{uuid4().hex}.bin"
        with (settings.bronze_dir / raw_path).open("xb") as destination:
            destination.write(content)
        entry.raw_path = raw_path
        session.commit()
        rows = parse_dataset(content, file_type, schema_type)
        dataset = session.scalar(select(Dataset).where(Dataset.name == name))
        if dataset and dataset.source_id != source.id:
            raise ValueError("That dataset name belongs to another source.")
        if dataset is None:
            dataset = Dataset(name=name, source_id=source.id)
            session.add(dataset)
            session.flush()
        if schema_type == "aggregate":
            for values in rows:
                programme = session.scalar(
                    select(Programme).where(Programme.name == values["name"])
                )
                if programme is None:
                    session.add(Programme(**values))
                else:
                    for field, value in values.items():
                        setattr(programme, field, value)
        now = datetime.now(UTC)
        entry.dataset_id = dataset.id
        entry.records_received = len(rows)
        entry.status = "succeeded"
        entry.completed_at = now
        session.execute(
            update(DataSource)
            .where(DataSource.id == source.id)
            .values(
                records_count=DataSource.records_count + len(rows),
                last_synced_at=now,
                status="active",
            )
        )
        session.add(
            IngestionRecord(source_id=source.id, records_ingested=len(rows), ingested_at=now)
        )
        session.commit()
    except (ValueError, ConnectorError) as error:
        session.rollback()
        entry.status = "failed"
        entry.error_message = str(error)[:500]
        entry.completed_at = datetime.now(UTC)
        source.status = "error"
        session.commit()
        code = 502 if isinstance(error, ConnectorError) else 422
        raise HTTPException(
            status_code=code, detail=f"Import failed: {entry.error_message}"
        ) from None
    except (OSError, SQLAlchemyError) as error:
        logger.error("Dataset import %s failed (%s).", entry.id, type(error).__name__)
        session.rollback()
        entry.status = "failed"
        entry.error_message = "Storage or database operation failed."
        entry.completed_at = datetime.now(UTC)
        source.status = "error"
        session.commit()
        raise HTTPException(status_code=503, detail=entry.error_message) from None
    session.refresh(entry)
    return entry


@router.get("", response_model=list[DatasetImportRead])
def list_imports(
    session: DbSession,
    source_type: str | None = None,
    import_status: Literal["running", "succeeded", "failed"] | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[DatasetImport]:
    if from_date and to_date and from_date > to_date:
        raise HTTPException(status_code=422, detail="Start date must not be after end date.")
    query = select(DatasetImport)
    if source_type:
        query = query.where(DatasetImport.source_type == source_type)
    if import_status:
        query = query.where(DatasetImport.status == import_status)
    if from_date:
        query = query.where(DatasetImport.created_at >= datetime.combine(from_date, time.min, UTC))
    if to_date and to_date < date.max:
        query = query.where(
            DatasetImport.created_at < datetime.combine(to_date + timedelta(days=1), time.min, UTC)
        )
    return list(session.scalars(query.order_by(DatasetImport.created_at.desc()).limit(limit)))
