"""Server-bound identities for the local demonstration.

Tokens are provisioned outside the browser build. Request headers never supply
the role or employee ID; those values come from server configuration only.
"""

import hmac
import json
import os
from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, status

DemoRole = Literal["employee", "hr"]
_PUBLIC_ENVIRONMENTS = {"cloud", "production", "prod", "staging"}
router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@dataclass(frozen=True)
class DemoPrincipal:
    role: DemoRole
    employee_id: str | None


def _configured_principals() -> dict[str, DemoPrincipal]:
    hr_token = os.getenv("DEMO_HR_TOKEN", "").strip()
    raw_employee_tokens = os.getenv("DEMO_EMPLOYEE_TOKENS", "{}").strip() or "{}"
    try:
        employee_tokens = json.loads(raw_employee_tokens)
    except json.JSONDecodeError as error:
        raise RuntimeError("DEMO_EMPLOYEE_TOKENS must be a JSON object") from error
    if not isinstance(employee_tokens, dict):
        raise RuntimeError("DEMO_EMPLOYEE_TOKENS must be a JSON object")
    if not hr_token and not employee_tokens:
        raise RuntimeError("Set DEMO_HR_TOKEN or DEMO_EMPLOYEE_TOKENS before starting the demo API")

    principals: dict[str, DemoPrincipal] = {}
    if hr_token:
        principals[hr_token] = DemoPrincipal(role="hr", employee_id=None)
    for employee_id, token in employee_tokens.items():
        if not isinstance(employee_id, str) or not employee_id.strip():
            raise RuntimeError("DEMO_EMPLOYEE_TOKENS contains an empty employee ID")
        if not isinstance(token, str) or not token.strip():
            raise RuntimeError(f"DEMO_EMPLOYEE_TOKENS has no token for {employee_id!r}")
        if token in principals:
            raise RuntimeError("Demo tokens must be unique across identities")
        principals[token] = DemoPrincipal(role="employee", employee_id=employee_id)
    if any(len(token) < 16 for token in principals):
        raise RuntimeError("Demo tokens must contain at least 16 characters")
    return principals


def assert_auth_configuration() -> None:
    auth_mode = os.getenv("AUTH_MODE", "demo").strip().lower()
    if auth_mode != "demo":
        raise RuntimeError(
            f"AUTH_MODE={auth_mode!r} is not configured; install the OIDC/JWT adapter "
            "before enabling a non-demo authentication mode"
        )
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    is_public_runtime = app_env in _PUBLIC_ENVIRONMENTS or bool(os.getenv("VERCEL"))
    explicitly_allowed = os.getenv("ALLOW_INSECURE_DEMO_AUTH", "false").strip().lower() in {
        "1", "true", "yes"
    }
    if is_public_runtime and not explicitly_allowed:
        raise RuntimeError(
            "Demo bearer authentication is disabled in public environments. "
            "Configure verified OIDC/JWT authentication; for an access-gated "
            "temporary demo only, explicitly set ALLOW_INSECURE_DEMO_AUTH=true."
        )
    _configured_principals()


def get_demo_principal(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> DemoPrincipal:
    try:
        assert_auth_configuration()
        principals = _configured_principals()
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
    scheme, separator, token = (authorization or "").partition(" ")
    if not separator or scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    for configured_token, principal in principals.items():
        if hmac.compare_digest(configured_token.encode("utf-8"), token.encode("utf-8")):
            return principal
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid bearer token",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.get("/me")
def auth_me(
    principal: Annotated[DemoPrincipal, Depends(get_demo_principal)],
) -> dict[str, str | None]:
    return {"role": principal.role, "employee_id": principal.employee_id}


def require_hr(
    principal: Annotated[DemoPrincipal, Depends(get_demo_principal)],
) -> DemoPrincipal:
    if principal.role != "hr":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="HR role required")
    return principal


def require_employee_access(
    employee_id: str,
    principal: Annotated[DemoPrincipal, Depends(get_demo_principal)],
) -> DemoPrincipal:
    if principal.role == "employee" and principal.employee_id != employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employees can access only their own resources",
        )
    return principal


HRPrincipal = Annotated[DemoPrincipal, Depends(require_hr)]
EmployeeResourcePrincipal = Annotated[DemoPrincipal, Depends(require_employee_access)]
