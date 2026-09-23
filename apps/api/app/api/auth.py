from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Depends, Header, HTTPException, status

DemoRole = Literal["employee", "hr"]


@dataclass(frozen=True)
class DemoPrincipal:
    """Identity supplied by the hackathon demo role switch.

    The headers are deliberately explicit so that hiding a button in the web app
    is never the authorization boundary. A production identity provider can
    replace this dependency without changing application services.
    """

    role: DemoRole
    employee_id: str | None


def get_demo_principal(
    role: Annotated[str, Header(alias="X-Demo-Role")] = "employee",
    x_employee_id: Annotated[str | None, Header(alias="X-Employee-Id")] = None,
) -> DemoPrincipal:
    normalized_role = role.strip().lower()
    if normalized_role not in {"employee", "hr"}:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unknown demo role",
        )
    normalized_employee_id = x_employee_id.strip() if x_employee_id else None
    return DemoPrincipal(
        role=normalized_role,  # type: ignore[arg-type]
        employee_id=normalized_employee_id,
    )


def require_hr(
    principal: Annotated[DemoPrincipal, Depends(get_demo_principal)],
) -> DemoPrincipal:
    if principal.role != "hr":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="HR role required",
        )
    return principal


def require_employee_access(
    employee_id: str,
    principal: Annotated[DemoPrincipal, Depends(get_demo_principal)],
) -> DemoPrincipal:
    """Allow HR drill-down and prevent employees reading another profile."""

    if principal.role == "employee" and principal.employee_id != employee_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employees can access only their own resources",
        )
    return principal


HRPrincipal = Annotated[DemoPrincipal, Depends(require_hr)]
EmployeeResourcePrincipal = Annotated[DemoPrincipal, Depends(require_employee_access)]
