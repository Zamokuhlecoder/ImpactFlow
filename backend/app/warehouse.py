"""Silver-to-warehouse loading for the fields currently supported by ImpactFlow."""

import json
import re
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import (
    DimBeneficiary,
    DimDate,
    DimIndicator,
    DimLocation,
    DimProgramme,
    FactBeneficiaryParticipation,
    FactProgrammeOutcome,
    Programme,
    TransformationRun,
    WarehouseLoad,
)


def _key(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value).strip().casefold()).strip("-")


def _date_dimension(session: Session, value: date) -> DimDate:
    current = session.scalar(select(DimDate).where(DimDate.full_date == value))
    if current:
        return current
    current = DimDate(
        date_key=int(value.strftime("%Y%m%d")),
        full_date=value,
        day=value.day,
        month=value.month,
        month_name=value.strftime("%B"),
        quarter=(value.month - 1) // 3 + 1,
        year=value.year,
    )
    session.add(current)
    session.flush()
    return current


def _location_dimension(session: Session, province: str) -> DimLocation:
    current = session.scalar(
        select(DimLocation).where(
            DimLocation.province == province,
            DimLocation.district.is_(None),
            DimLocation.municipality.is_(None),
            DimLocation.location_name.is_(None),
        )
    )
    if current:
        return current
    current = DimLocation(province=province)
    session.add(current)
    session.flush()
    return current


def _programme_dimension(
    session: Session, name: str, source_programme: Programme | None = None
) -> DimProgramme:
    programme_id = str(source_programme.id) if source_programme else f"silver:{_key(name)}"
    current = session.scalar(
        select(DimProgramme).where(DimProgramme.programme_id == programme_id)
    )
    if current:
        return current
    current = DimProgramme(
        programme_id=programme_id,
        programme_name=name,
        programme_category=source_programme.category if source_programme else None,
        programme_status=source_programme.status if source_programme else None,
    )
    session.add(current)
    session.flush()
    return current


def _beneficiary_dimension(session: Session, beneficiary_id: str, province: str) -> DimBeneficiary:
    current = session.scalar(
        select(DimBeneficiary).where(DimBeneficiary.beneficiary_id == beneficiary_id)
    )
    if current:
        return current
    current = DimBeneficiary(beneficiary_id=beneficiary_id, province=province)
    session.add(current)
    session.flush()
    return current


def _indicator_dimension(session: Session, indicator_id: str, name: str) -> DimIndicator:
    current = session.scalar(
        select(DimIndicator).where(DimIndicator.indicator_id == indicator_id)
    )
    if current:
        return current
    current = DimIndicator(
        indicator_id=indicator_id,
        indicator_name=name,
        indicator_category="programme delivery",
        measurement_unit="beneficiaries",
    )
    session.add(current)
    session.flush()
    return current


def _read_silver(path: Path) -> list[dict[str, Any]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list) or not all(isinstance(row, dict) for row in value):
        raise ValueError("The Silver artifact is invalid.")
    return value


def load_transformation_run(
    session: Session,
    run: TransformationRun,
    silver_path: Path,
) -> WarehouseLoad:
    """Load a completed Silver artifact without duplicating its fact grain."""
    existing = session.scalar(
        select(WarehouseLoad).where(WarehouseLoad.transformation_run_id == run.id)
    )
    if existing:
        return existing
    load = WarehouseLoad(
        id=uuid4(),
        transformation_run_id=run.id,
        status="running",
        started_at=datetime.now(UTC),
    )
    session.add(load)
    session.flush()
    try:
        rows = _read_silver(silver_path)
        load.records_received = len(rows)
        loaded = 0
        skipped = 0
        for row in rows:
            province = row.get("province")
            programme_name = row.get("programme") or row.get("name")
            if not isinstance(province, str) or not isinstance(programme_name, str):
                skipped += 1
                continue
            source_programme = session.scalar(
                select(Programme).where(Programme.name.ilike(programme_name))
            )
            programme = _programme_dimension(session, programme_name, source_programme)
            location = _location_dimension(session, province)
            if "beneficiary_id" in row:
                beneficiary_id = row.get("beneficiary_id")
                participation_date = row.get("participation_date")
                if not isinstance(beneficiary_id, str) or not isinstance(participation_date, str):
                    skipped += 1
                    continue
                parsed_date = date.fromisoformat(participation_date)
                date_dim = _date_dimension(session, parsed_date)
                beneficiary = _beneficiary_dimension(session, beneficiary_id, province)
                existing_fact = session.scalar(
                    select(FactBeneficiaryParticipation).where(
                        FactBeneficiaryParticipation.beneficiary_key == beneficiary.beneficiary_key,
                        FactBeneficiaryParticipation.programme_key == programme.programme_key,
                        FactBeneficiaryParticipation.location_key == location.location_key,
                        FactBeneficiaryParticipation.date_key == date_dim.date_key,
                    )
                )
                if existing_fact:
                    skipped += 1
                    continue
                session.add(FactBeneficiaryParticipation(
                    beneficiary_key=beneficiary.beneficiary_key,
                    programme_key=programme.programme_key,
                    location_key=location.location_key,
                    date_key=date_dim.date_key,
                    participation_count=1,
                ))
                loaded += 1
            elif "target_beneficiaries" in row:
                report_date = datetime.now(UTC).date()
                date_dim = _date_dimension(session, report_date)
                indicator = _indicator_dimension(
                    session, "beneficiaries-reached", "Beneficiaries reached"
                )
                existing_fact = session.scalar(
                    select(FactProgrammeOutcome).where(
                        FactProgrammeOutcome.programme_key == programme.programme_key,
                        FactProgrammeOutcome.location_key == location.location_key,
                        FactProgrammeOutcome.indicator_key == indicator.indicator_key,
                        FactProgrammeOutcome.date_key == date_dim.date_key,
                    )
                )
                if existing_fact:
                    skipped += 1
                    continue
                target = float(row["target_beneficiaries"])
                actual = float(row.get("reached_beneficiaries") or 0)
                session.add(FactProgrammeOutcome(
                    programme_key=programme.programme_key,
                    location_key=location.location_key,
                    indicator_key=indicator.indicator_key,
                    date_key=date_dim.date_key,
                    target_value=target,
                    actual_value=actual,
                    achievement_percentage=round(actual / target * 100, 2) if target else None,
                ))
                loaded += 1
            else:
                skipped += 1
        load.records_loaded = loaded
        load.records_skipped = skipped
        load.status = "warning" if skipped else "succeeded"
        load.completed_at = datetime.now(UTC)
        session.commit()
    except (OSError, ValueError, TypeError, SQLAlchemyError) as error:
        session.rollback()
        load = session.get(WarehouseLoad, load.id)
        if load is None:
            raise
        load.status = "failed"
        load.error_details = str(error)[:500]
        load.completed_at = datetime.now(UTC)
        session.commit()
    return load
