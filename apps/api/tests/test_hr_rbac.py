from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.auth import assert_auth_configuration, require_employee_access, router as auth_router
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


def configure_auth(monkeypatch) -> None:
    monkeypatch.setenv("DEMO_HR_TOKEN", "test-hr-secret-123456789")
    monkeypatch.setenv(
        "DEMO_EMPLOYEE_TOKENS",
        '{"E0001":"test-employee-one-secret","E0002":"test-employee-two-secret"}',
    )


def test_hr_endpoints_reject_employee_role(monkeypatch) -> None:
    configure_auth(monkeypatch)
    client, _ = make_client()

    response = client.get(
        "/api/v1/hr/skill-gaps",
        headers={
            "Authorization": "Bearer test-employee-one-secret",
            "X-Demo-Role": "hr",
            "X-Employee-Id": "E0002",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "HR role required"


def test_hr_aggregates_real_seed_and_filters(monkeypatch) -> None:
    configure_auth(monkeypatch)
    client, service = make_client()
    employee = next(iter(service.bundle.employees.values()))
    headers = {"Authorization": "Bearer test-hr-secret-123456789"}

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


def test_employee_resource_dependency_blocks_cross_employee_access(monkeypatch) -> None:
    configure_auth(monkeypatch)
    application = FastAPI()
    application.include_router(auth_router)

    @application.get("/employees/{employee_id}")
    def protected(
        employee_id: str,
        _principal: Annotated[object, Depends(require_employee_access)],
    ) -> dict[str, str]:
        return {"employee_id": employee_id}

    client = TestClient(application)
    own = client.get(
        "/employees/E0001",
        headers={
            "Authorization": "Bearer test-employee-one-secret",
            "X-Demo-Role": "hr",
            "X-Employee-Id": "E0002",
        },
    )
    other = client.get(
        "/employees/E0002",
        headers={"Authorization": "Bearer test-employee-one-secret"},
    )
    hr_access = client.get(
        "/employees/E0002", headers={"Authorization": "Bearer test-hr-secret-123456789"}
    )
    spoofed = client.get(
        "/employees/E0002", headers={"X-Demo-Role": "hr", "X-Employee-Id": "E0002"}
    )
    me = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer test-employee-one-secret"}
    )

    assert own.status_code == 200
    assert other.status_code == 403
    assert hr_access.status_code == 200
    assert spoofed.status_code == 401
    assert me.json() == {"role": "employee", "employee_id": "E0001"}


def test_public_runtime_rejects_demo_bearer_auth(
    monkeypatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_MODE", "demo")
    monkeypatch.delenv("ALLOW_INSECURE_DEMO_AUTH", raising=False)
    configure_auth(monkeypatch)

    with pytest.raises(RuntimeError, match="disabled in public environments"):
        assert_auth_configuration()
