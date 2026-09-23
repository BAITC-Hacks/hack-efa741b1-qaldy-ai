import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.dependencies import assert_backend_ready

router = APIRouter(tags=["system"])
logger = logging.getLogger(__name__)


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str


def _healthy_response() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="career-quest-api",
        version="0.1.0",
    )


def _ready_response() -> HealthResponse:
    try:
        assert_backend_ready()
    except Exception as exc:
        logger.exception("Backend readiness check failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Required dataset or database is unavailable",
        ) from exc
    return _healthy_response()


@router.get("/livez", response_model=HealthResponse)
def livez() -> HealthResponse:
    """Process-only probe; it intentionally does not touch external dependencies."""
    return _healthy_response()


@router.get("/readyz", response_model=HealthResponse)
def readyz() -> HealthResponse:
    return _ready_response()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Backward-compatible readiness endpoint."""
    return _ready_response()
