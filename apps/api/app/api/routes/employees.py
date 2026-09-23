from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status

from app.api.auth import EmployeeActionPrincipal, EmployeeResourcePrincipal, HRPrincipal
from app.api.dependencies import get_journey_service
from app.api.schemas import (
    CompletionResponse,
    EmployeeJourneyResponse,
    EmployeeListItemResponse,
)
from app.application.journey_service import (
    CompletionConflict,
    EmployeeNotFound,
    EventNotFound,
    JourneyService,
)

router = APIRouter(prefix="/api/v1/employees", tags=["employees"])
Service = Annotated[JourneyService, Depends(get_journey_service)]


@router.get("", response_model=list[EmployeeListItemResponse])
def list_employees(
    service: Service,
    _principal: HRPrincipal,
    query: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=1000),
) -> list[EmployeeListItemResponse]:
    return [EmployeeListItemResponse.model_validate(item) for item in service.list_employees(query, limit)]


@router.get("/{employee_id}/journey", response_model=EmployeeJourneyResponse)
def employee_journey(
    employee_id: str,
    service: Service,
    _principal: EmployeeResourcePrincipal,
) -> EmployeeJourneyResponse:
    try:
        return EmployeeJourneyResponse.model_validate(service.get_journey(employee_id))
    except EmployeeNotFound as error:
        raise HTTPException(status_code=404, detail="Employee not found") from error


@router.post("/{employee_id}/recommendations", response_model=EmployeeJourneyResponse)
def recommendations(
    employee_id: str,
    service: Service,
    _principal: EmployeeResourcePrincipal,
) -> EmployeeJourneyResponse:
    try:
        return EmployeeJourneyResponse.model_validate(
            service.get_recommendations(employee_id)
        )
    except EmployeeNotFound as error:
        raise HTTPException(status_code=404, detail="Employee not found") from error


@router.post(
    "/{employee_id}/activities/{event_id}/complete",
    response_model=CompletionResponse,
)
def complete_activity(
    employee_id: str,
    event_id: str,
    service: Service,
    _principal: EmployeeActionPrincipal,
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=1, max_length=128)
    ],
) -> CompletionResponse:
    try:
        result = service.complete_activity(employee_id, event_id, idempotency_key)
        return CompletionResponse.model_validate(result)
    except EmployeeNotFound as error:
        raise HTTPException(status_code=404, detail="Employee not found") from error
    except EventNotFound as error:
        raise HTTPException(status_code=404, detail="Event not found") from error
    except CompletionConflict as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
