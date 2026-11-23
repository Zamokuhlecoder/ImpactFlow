from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.models import (
    DimBeneficiary,
    DimIndicator,
    DimLocation,
    DimOrganisation,
    DimProgramme,
    FactBeneficiaryParticipation,
    FactExpenditure,
    FactProgrammeOutcome,
    WarehouseLoad,
)
from app.schemas.warehouse import (
    AnalyticsUnavailableRead,
    BeneficiaryParticipationRead,
    ProgrammePerformanceRead,
    ProvincialPerformanceRead,
    WarehouseLoadRead,
    WarehouseOverviewRead,
)

router = APIRouter(prefix="/warehouse", tags=["Analytical warehouse"])
analytics_router = APIRouter(prefix="/analytics", tags=["Warehouse analytics"])
DbSession = Annotated[Session, Depends(get_db_session)]


@router.get("/overview", response_model=WarehouseOverviewRead)
def warehouse_overview(session: DbSession) -> WarehouseOverviewRead:
    dimension_models = {
        "beneficiaries": DimBeneficiary,
        "programmes": DimProgramme,
        "locations": DimLocation,
        "organisations": DimOrganisation,
        "indicators": DimIndicator,
    }
    fact_models = {
        "participation": FactBeneficiaryParticipation,
        "programme_outcomes": FactProgrammeOutcome,
        "expenditure": FactExpenditure,
    }
    dimensions = {
        name: session.scalar(select(func.count()).select_from(model)) or 0
        for name, model in dimension_models.items()
    }
    facts = {
        name: session.scalar(select(func.count()).select_from(model)) or 0
        for name, model in fact_models.items()
    }
    latest_load = session.scalar(select(WarehouseLoad).order_by(WarehouseLoad.started_at.desc()))
    return WarehouseOverviewRead(
        dimensions=dimensions,
        facts=facts,
        latest_load=latest_load,
        supported_fields=[
            "beneficiary_id", "programme", "province", "participation_date",
            "target_beneficiaries", "reached_beneficiaries",
        ],
        unavailable_fields=[
            "gender", "registration_date", "district", "municipality",
            "expenditure", "assessments",
        ],
    )


@router.get("/loads", response_model=list[WarehouseLoadRead])
def warehouse_loads(
    session: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[WarehouseLoad]:
    return list(
        session.scalars(
            select(WarehouseLoad).order_by(WarehouseLoad.started_at.desc()).limit(limit)
        )
    )


@analytics_router.get("/programme-performance", response_model=list[ProgrammePerformanceRead])
def programme_performance(session: DbSession) -> list[ProgrammePerformanceRead]:
    rows = session.execute(
        select(
            DimProgramme.programme_name,
            DimLocation.province,
            FactProgrammeOutcome.target_value,
            FactProgrammeOutcome.actual_value,
            FactProgrammeOutcome.achievement_percentage,
        )
        .join(DimProgramme, DimProgramme.programme_key == FactProgrammeOutcome.programme_key)
        .join(DimLocation, DimLocation.location_key == FactProgrammeOutcome.location_key)
        .order_by(DimProgramme.programme_name)
    )
    return [
        ProgrammePerformanceRead(
            programme=name,
            province=province,
            target=target,
            actual=actual,
            achievement_percentage=achievement,
        )
        for name, province, target, actual, achievement in rows
    ]


@analytics_router.get("/provincial-performance", response_model=list[ProvincialPerformanceRead])
def provincial_performance(session: DbSession) -> list[ProvincialPerformanceRead]:
    rows = session.execute(
        select(
            DimLocation.province,
            func.count(func.distinct(FactBeneficiaryParticipation.programme_key)),
            func.coalesce(func.sum(FactBeneficiaryParticipation.participation_count), 0),
        )
        .join(
            FactBeneficiaryParticipation,
            FactBeneficiaryParticipation.location_key == DimLocation.location_key,
        )
        .group_by(DimLocation.province)
        .order_by(DimLocation.province)
    )
    return [
        ProvincialPerformanceRead(
            province=province, programmes=programmes, participants=participants
        )
        for province, programmes, participants in rows
    ]


@analytics_router.get(
    "/beneficiary-participation",
    response_model=list[BeneficiaryParticipationRead],
)
def beneficiary_participation(session: DbSession) -> list[BeneficiaryParticipationRead]:
    rows = session.execute(
        select(
            DimBeneficiary.beneficiary_id,
            func.count(func.distinct(FactBeneficiaryParticipation.programme_key)),
            func.count(FactBeneficiaryParticipation.participation_key),
        )
        .join(
            FactBeneficiaryParticipation,
            FactBeneficiaryParticipation.beneficiary_key == DimBeneficiary.beneficiary_key,
        )
        .group_by(DimBeneficiary.beneficiary_id)
        .order_by(DimBeneficiary.beneficiary_id)
    )
    return [
        BeneficiaryParticipationRead(
            beneficiary_id=beneficiary_id,
            programmes=programmes,
            participation_records=records,
        )
        for beneficiary_id, programmes, records in rows
    ]


@analytics_router.get("/expenditure", response_model=AnalyticsUnavailableRead)
def expenditure_analytics() -> AnalyticsUnavailableRead:
    return AnalyticsUnavailableRead(
        reason="Expenditure fields are not present in the supported Silver schemas."
    )


@analytics_router.get("/indicator-performance", response_model=AnalyticsUnavailableRead)
def indicator_performance() -> AnalyticsUnavailableRead:
    return AnalyticsUnavailableRead(
        reason=(
            "Assessment and indicator result fields are not present "
            "in the supported Silver schemas."
        )
    )
