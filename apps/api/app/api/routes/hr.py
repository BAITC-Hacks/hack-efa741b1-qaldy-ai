from typing import Annotated, cast

from fastapi import APIRouter, Depends, Query

from app.api.auth import HRPrincipal
from app.api.dependencies import get_journey_service
from app.api.hr_schemas import (
    CatalogGapsResponse,
    ParticipationResponse,
    SkillGapsResponse,
    UncoveredEmployeesResponse,
)
from app.application.hr_service import HRFilters, HRService
from app.application.journey_service import JourneyService
from app.domain.models import Grade

router = APIRouter(prefix="/api/v1/hr", tags=["hr"])


def get_hr_service(
    journey_service: Annotated[JourneyService, Depends(get_journey_service)],
) -> HRService:
    return HRService(journey_service)


HRServiceDependency = Annotated[HRService, Depends(get_hr_service)]


def filters_from_query(
    department: str | None = Query(default=None, max_length=100),
    role: str | None = Query(default=None, max_length=100),
    grade: str | None = Query(default=None, pattern="^(Junior|Middle|Senior|Lead)$"),
) -> HRFilters:
    return HRFilters(
        department=department,
        role=role,
        grade=cast(Grade | None, grade),
    )


Filters = Annotated[HRFilters, Depends(filters_from_query)]


@router.get("/skill-gaps", response_model=SkillGapsResponse)
def skill_gaps(
    service: HRServiceDependency,
    filters: Filters,
    _principal: HRPrincipal,
) -> dict[str, object]:
    return service.skill_gaps(filters)


@router.get("/participation", response_model=ParticipationResponse)
def participation(
    service: HRServiceDependency,
    filters: Filters,
    _principal: HRPrincipal,
) -> dict[str, object]:
    return service.participation(filters)


@router.get("/uncovered-employees", response_model=UncoveredEmployeesResponse)
def uncovered_employees(
    service: HRServiceDependency,
    filters: Filters,
    _principal: HRPrincipal,
) -> dict[str, object]:
    return service.uncovered_employees(filters)


@router.get("/catalog-gaps", response_model=CatalogGapsResponse)
def catalog_gaps(
    service: HRServiceDependency,
    filters: Filters,
    _principal: HRPrincipal,
) -> dict[str, object]:
    return service.catalog_gaps(filters)
