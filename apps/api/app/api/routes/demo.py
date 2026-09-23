from fastapi import APIRouter

from app.application.demo_journey import get_demo_employee_journey
from app.domain.journey import EmployeeJourney

router = APIRouter()


@router.get("/employee-journey", response_model=EmployeeJourney)
def employee_journey() -> EmployeeJourney:
    """Return the first runnable employee-facing vertical slice."""
    return get_demo_employee_journey()
