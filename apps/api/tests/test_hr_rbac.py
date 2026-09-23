from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.auth import require_employee_access
from app.api.dependencies import get_journey_service
from app.api.routes import hr
from app.application.journey_service import JourneyService
from app.infrastructure.dataset_loader import load_dataset


def make_client() -> tuple[TestClient, JourneyService]:
    service = JourneyService(load_dataset())
    application = FastAPI()
    application.include_router(hr.router)
    application.dependency_overrides[get_journey_service] = lambda: service
    return TestClient(application), service


def test_hr_endpoints_reject_employee_role() -> None:
    client, _ = make_client()

    response = client.get(
        "/api/v1/hr/skill-gaps",
        headers={"X-Demo-Role": "employee", "X-Employee-Id": "E0001"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "HR role required"


def test_hr_aggregates_real_seed_and_filters() -> None:
    client, service = make_client()
    employee = next(iter(service.bundle.employees.values()))
    headers = {"X-Demo-Role": "hr"}

    gaps = client.get(
        "/api/v1/hr/skill-gaps",
        params={"department": employee.department},
        headers=headers,
    )
    participation = client.get("/api/v1/hr/participation", headers=headers)
    uncovered = client.get("/api/v1/hr/uncovered-employees", headers=headers)
    catalog = client.get("/api/v1/hr/catalog-gaps", headers=headers)

    assert gaps.status_code == 200
    assert gaps.json()["employee_count"] == sum(
        item.department == employee.department for item in service.bundle.employees.values()
    )
    assert gaps.json()["items"]
    assert participation.status_code == 200
    assert participation.json()["total_records"] == len(service.bundle.history)
    assert sum(participation.json()["statuses"].values()) == len(service.bundle.history)
    assert uncovered.status_code == 200
    assert all(not item["employee_id"].startswith("unknown") for item in uncovered.json()["items"])
    assert catalog.status_code == 200
    assert any(item["skill_id"] == "SK_TEST_DESIGN" for item in catalog.json()["items"])


def test_employee_resource_dependency_blocks_cross_employee_access() -> None:
    application = FastAPI()

    @application.get("/employees/{employee_id}")
    def protected(
        employee_id: str,
        _principal: Annotated[object, Depends(require_employee_access)],
    ) -> dict[str, str]:
        return {"employee_id": employee_id}

    client = TestClient(application)
    own = client.get(
        "/employees/E0001",
        headers={"X-Demo-Role": "employee", "X-Employee-Id": "E0001"},
    )
    other = client.get(
        "/employees/E0002",
        headers={"X-Demo-Role": "employee", "X-Employee-Id": "E0001"},
    )
    hr_access = client.get("/employees/E0002", headers={"X-Demo-Role": "hr"})

    assert own.status_code == 200
    assert other.status_code == 403
    assert hr_access.status_code == 200
