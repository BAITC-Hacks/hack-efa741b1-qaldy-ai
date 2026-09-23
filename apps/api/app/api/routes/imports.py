from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.api.auth import HRPrincipal
from app.api.dependencies import get_import_service
from app.api.import_schemas import (
    ImportApplyRequest,
    ImportApplyResponse,
    ImportValidateRequest,
    ImportValidationResponse,
)
from app.application.import_service import ImportConflict, ImportService, ValidationTokenError

router = APIRouter(prefix="/api/v1/import", tags=["import"])
Service = Annotated[ImportService, Depends(get_import_service)]


@router.post("/validate", response_model=ImportValidationResponse)
def validate_import(
    body: ImportValidateRequest,
    service: Service,
    _principal: HRPrincipal,
) -> ImportValidationResponse:
    result = service.validate(body.employees_json, body.activity_history_csv)
    return ImportValidationResponse.model_validate(result, from_attributes=True)


@router.post("/apply", response_model=ImportApplyResponse)
def apply_import(
    body: ImportApplyRequest,
    service: Service,
    idempotency_key: Annotated[
        str, Header(alias="Idempotency-Key", min_length=1, max_length=128)
    ],
    _principal: HRPrincipal,
) -> ImportApplyResponse:
    try:
        result = service.apply(
            body.validation_token,
            body.package_hash,
            idempotency_key,
        )
        return ImportApplyResponse.model_validate(result, from_attributes=True)
    except ValidationTokenError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except ImportConflict as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
