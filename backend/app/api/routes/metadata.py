from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.models import Dataset, DataSource, Location, Organisation
from app.schemas.domain import (
    DatasetInput,
    DatasetRead,
    DatasetUpdate,
    LocationInput,
    LocationRead,
    LocationUpdate,
    OrganisationInput,
    OrganisationRead,
    OrganisationUpdate,
)

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db_session)]
Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]


def _commit_named(session: Session, item: Organisation | Dataset) -> None:
    model = type(item)
    name = item.name
    item_id = item.id
    source_id = item.source_id if isinstance(item, Dataset) else None
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        duplicate = select(model.id).where(model.name == name)
        if item_id is not None:
            duplicate = duplicate.where(model.id != item_id)
        if session.scalar(duplicate) is not None:
            raise HTTPException(
                status_code=409, detail="A record with this name already exists."
            ) from None
        if source_id is not None and session.get(DataSource, source_id) is None:
            raise HTTPException(status_code=409, detail="Data source not found.") from None
        raise
    session.refresh(item)


def _require_source(session: Session, source_id: UUID | None) -> None:
    if source_id is not None and session.get(DataSource, source_id) is None:
        raise HTTPException(status_code=404, detail="Data source not found.")


@router.get("/organisations", response_model=list[OrganisationRead], tags=["organisations"])
def list_organisations(
    session: DbSession, limit: Limit = 50, offset: Offset = 0
) -> list[Organisation]:
    return list(
        session.scalars(
            select(Organisation).order_by(Organisation.name).limit(limit).offset(offset)
        )
    )


@router.post(
    "/organisations", response_model=OrganisationRead, status_code=201, tags=["organisations"]
)
def create_organisation(payload: OrganisationInput, session: DbSession) -> Organisation:
    item = Organisation(**payload.model_dump())
    session.add(item)
    _commit_named(session, item)
    return item


@router.patch("/organisations/{item_id}", response_model=OrganisationRead, tags=["organisations"])
def update_organisation(
    item_id: UUID, payload: OrganisationUpdate, session: DbSession
) -> Organisation:
    item = session.get(Organisation, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    item.name = payload.name
    _commit_named(session, item)
    return item


@router.delete(
    "/organisations/{item_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["organisations"]
)
def delete_organisation(item_id: UUID, session: DbSession) -> None:
    item = session.get(Organisation, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Organisation not found.")
    session.delete(item)
    session.commit()


@router.get("/locations", response_model=list[LocationRead], tags=["locations"])
def list_locations(session: DbSession, limit: Limit = 50, offset: Offset = 0) -> list[Location]:
    return list(
        session.scalars(
            select(Location)
            .order_by(Location.province, Location.district, Location.area, Location.id)
            .limit(limit)
            .offset(offset)
        )
    )


@router.post("/locations", response_model=LocationRead, status_code=201, tags=["locations"])
def create_location(payload: LocationInput, session: DbSession) -> Location:
    item = Location(**payload.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


@router.patch("/locations/{item_id}", response_model=LocationRead, tags=["locations"])
def update_location(
    item_id: UUID, payload: LocationUpdate, session: DbSession
) -> Location:
    item = session.get(Location, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Location not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    session.commit()
    session.refresh(item)
    return item


@router.delete("/locations/{item_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["locations"])
def delete_location(item_id: UUID, session: DbSession) -> None:
    item = session.get(Location, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Location not found.")
    session.delete(item)
    session.commit()


@router.get("/datasets", response_model=list[DatasetRead], tags=["datasets"])
def list_datasets(session: DbSession, limit: Limit = 50, offset: Offset = 0) -> list[Dataset]:
    return list(session.scalars(select(Dataset).order_by(Dataset.name).limit(limit).offset(offset)))


@router.post("/datasets", response_model=DatasetRead, status_code=201, tags=["datasets"])
def create_dataset(payload: DatasetInput, session: DbSession) -> Dataset:
    _require_source(session, payload.source_id)
    item = Dataset(**payload.model_dump())
    session.add(item)
    _commit_named(session, item)
    return item


@router.patch("/datasets/{item_id}", response_model=DatasetRead, tags=["datasets"])
def update_dataset(
    item_id: UUID, payload: DatasetUpdate, session: DbSession
) -> Dataset:
    item = session.get(Dataset, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    _require_source(session, payload.source_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    _commit_named(session, item)
    return item


@router.delete("/datasets/{item_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["datasets"])
def delete_dataset(item_id: UUID, session: DbSession) -> None:
    item = session.get(Dataset, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    session.delete(item)
    session.commit()
