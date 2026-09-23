from dataclasses import replace

from fastapi.testclient import TestClient

from app.api.dependencies import get_journey_service
from app.application.journey_service import JourneyService
from app.domain.models import RoleProfile
from app.infrastructure.dataset_loader import load_dataset
from app.main import app


def service_with_recommendation() -> tuple[JourneyService, str]:
    service = JourneyService(load_dataset())
    for employee_id in sorted(service.bundle.employees):
        if service.get_journey(employee_id).recommendations:
            return service, employee_id
    raise AssertionError("Seed must contain an employee with a valid recommendation")


def test_real_journey_is_explainable_and_deterministic() -> None:
    service, employee_id = service_with_recommendation()

    first = service.get_journey(employee_id)
    second = service.get_journey(employee_id)

    assert first.source == "dataset"
    assert first.dataset_version == "1.0"
    assert 1 <= len(first.recommendations) <= 3
    assert [item.event_id for item in first.recommendations] == [
        item.event_id for item in second.recommendations
    ]
    assert all(len(item.reasons) >= 3 for item in first.recommendations)
    assert all(abs(sum(item.weight for item in rec.factors) - 1.0) < 0.0001 for rec in first.recommendations)


def test_same_role_promotion_accepts_events_for_target_grade() -> None:
    bundle = load_dataset()
    employee = next(
        item for item in bundle.employees.values() if item.grade == "Junior"
    )
    event = replace(
        next(iter(bundle.events.values())),
        target_roles=frozenset({employee.role}),
        target_grades=frozenset({"Senior"}),
    )
    target = RoleProfile(
        role=employee.role,
        grade="Senior",
        required_skills={},
        critical_skills=frozenset(),
    )

    assert JourneyService._candidate_kind(employee, target, event) == "bridge"


def test_completion_updates_progress_once() -> None:
    service, employee_id = service_with_recommendation()
    before = service.get_journey(employee_id)
    event_id = before.recommendations[0].event_id

    result = service.complete_activity(employee_id, event_id, "test-completion-1")
    replay = service.complete_activity(employee_id, event_id, "test-completion-1")

    assert any(change.applied_gain > 0 for change in result.changes)
    assert result.journey.progress.current_points > before.progress.current_points
    assert replay.record_id == result.record_id
    assert replay.idempotent_replay is True


def test_api_employee_journey_and_completion() -> None:
    service, employee_id = service_with_recommendation()
    app.dependency_overrides[get_journey_service] = lambda: service
    client = TestClient(app)
    headers = {"X-Demo-Role": "employee", "X-Employee-Id": employee_id}
    try:
        journey = client.get(
            f"/api/v1/employees/{employee_id}/journey",
            headers=headers,
        )
        assert journey.status_code == 200
        body = journey.json()
        event_id = body["recommendations"][0]["event_id"]

        completion = client.post(
            f"/api/v1/employees/{employee_id}/activities/{event_id}/complete",
            headers={**headers, "Idempotency-Key": "api-flow-1"},
        )

        assert completion.status_code == 200
        assert completion.json()["journey"]["source"] == "dataset"
        assert completion.json()["changes"]
    finally:
        app.dependency_overrides.clear()
