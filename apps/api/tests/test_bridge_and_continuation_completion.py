from dataclasses import replace

import pytest

from app.application.journey_service import CompletionConflict, JourneyService
from app.domain.models import RoleProfile
from app.infrastructure.dataset_loader import load_dataset


def test_same_grade_cross_role_goals_admit_target_role_bridge_candidates() -> None:
    bundle = load_dataset()
    employees = [
        employee
        for employee in bundle.employees.values()
        if employee.career_goal is not None
        and employee.career_goal.target_role != employee.role
        and employee.career_goal.target_grade == employee.grade
    ]

    assert len(employees) == 28
    for employee in employees:
        target = bundle.role_profiles[
            (employee.career_goal.target_role, employee.career_goal.target_grade)
        ]
        target_events = [
            event
            for event in bundle.events.values()
            if target.role in event.target_roles
        ]
        assert any(
            JourneyService._candidate_kind(employee, target, event) == "bridge"
            for event in target_events
        ), employee.employee_id


def test_cross_role_bridge_never_exceeds_target_grade() -> None:
    bundle = load_dataset()
    employee = next(
        employee
        for employee in bundle.employees.values()
        if employee.career_goal is not None
        and employee.career_goal.target_role != employee.role
        and employee.career_goal.target_grade == "Middle"
    )
    target = bundle.role_profiles[
        (employee.career_goal.target_role, employee.career_goal.target_grade)
    ]
    event = replace(
        next(iter(bundle.events.values())),
        target_roles=frozenset({target.role}),
        target_grades=frozenset({"Senior"}),
    )

    assert JourneyService._candidate_kind(employee, target, event) is None


def test_in_progress_continuation_can_be_completed_idempotently() -> None:
    service = JourneyService(load_dataset())
    before = service.get_journey("E0004")
    event_id = "EV_025"

    assert event_id in {item.event_id for item in before.continuations}
    assert event_id not in {item.event_id for item in before.recommendations}

    result = service.complete_activity("E0004", event_id, "continue-e0004-ev025")
    replay = service.complete_activity("E0004", event_id, "continue-e0004-ev025")

    assert result.idempotent_replay is False
    assert event_id not in {item.event_id for item in result.journey.continuations}
    assert any(
        item.event_id == event_id and item.status == "completed"
        for item in result.journey.activity_history
    )
    assert replay.record_id == result.record_id
    assert replay.idempotent_replay is True


def test_completion_still_rejects_event_outside_active_lanes() -> None:
    service = JourneyService(load_dataset())
    employee_id = "E0004"
    journey = service.get_journey(employee_id)
    active = {
        item.event_id for item in journey.recommendations
    } | {item.event_id for item in journey.continuations}
    unavailable_event_id = next(
        event_id for event_id in sorted(service.bundle.events) if event_id not in active
    )

    with pytest.raises(
        CompletionConflict,
        match="not an active recommendation or continuation",
    ):
        service.complete_activity(
            employee_id,
            unavailable_event_id,
            "reject-unavailable-event",
        )
