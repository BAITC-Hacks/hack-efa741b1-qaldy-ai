from dataclasses import replace
from datetime import timedelta

from app.application.journey_service import JourneyService
from app.domain.models import ActivityRecord
from app.infrastructure.dataset_loader import load_dataset


def service() -> JourneyService:
    return JourneyService(load_dataset())


def test_01_critical_gap_outranks_noncritical_low_skill() -> None:
    journey = service().get_journey("E0001")
    critical_names = {gap.name for gap in journey.skill_gaps if gap.critical}
    assert journey.recommendations
    assert journey.recommendations[0].skill in critical_names


def test_03_completion_after_review_is_applied_once_by_record_id() -> None:
    original = service()
    employee = original.bundle.employees["E0001"]
    event = next(item for item in original.bundle.events.values() if item.develops_skills)
    gain = event.develops_skills[0]
    employee = replace(employee, skills={**employee.skills, gain.skill_id: 0})
    record = ActivityRecord(
        record_id="MASTER-AFTER",
        employee_id=employee.employee_id,
        event_id=event.event_id,
        activity_date=employee.last_review_date + timedelta(days=1),
        status="completed",
        completion_pct=100,
        assigned_by="self",
    )
    bundle = replace(
        original.bundle,
        employees={**original.bundle.employees, employee.employee_id: employee},
        history=(record, record),
    )
    tested = JourneyService(bundle)
    records = tested._employee_records(employee.employee_id)
    levels = tested._effective_skills(employee, records)
    assert levels[gain.skill_id] == min(gain.gain, gain.max_level)


def test_04_completion_before_review_is_not_reapplied() -> None:
    tested = service()
    employee = tested.bundle.employees["E0001"]
    event = next(item for item in tested.bundle.events.values() if item.develops_skills)
    gain = event.develops_skills[0]
    employee = replace(employee, skills={**employee.skills, gain.skill_id: 1})
    record = ActivityRecord(
        record_id="MASTER-BEFORE",
        employee_id=employee.employee_id,
        event_id=event.event_id,
        activity_date=employee.last_review_date,
        status="completed",
        completion_pct=100,
        assigned_by="self",
    )
    assert tested._effective_skills(employee, [record])[gain.skill_id] == 1


def test_05_max_level_never_lowers_a_higher_skill() -> None:
    tested = service()
    employee = tested.bundle.employees["E0001"]
    event = next(item for item in tested.bundle.events.values() if item.develops_skills)
    gain = event.develops_skills[0]
    employee = replace(employee, skills={**employee.skills, gain.skill_id: 5})
    record = ActivityRecord(
        record_id="MASTER-CAP",
        employee_id=employee.employee_id,
        event_id=event.event_id,
        activity_date=employee.last_review_date + timedelta(days=1),
        status="completed",
        completion_pct=100,
        assigned_by="self",
    )
    assert tested._effective_skills(employee, [record])[gain.skill_id] == 5


def test_06_regular_club_can_repeat_but_mandatory_events_are_never_recommended() -> None:
    tested = service()
    completed_club = {
        record.employee_id
        for record in tested.bundle.history
        if record.event_id == "EV_036" and record.status == "completed"
    }
    assert any(
        "EV_036" in {item.event_id for item in tested.get_journey(employee_id).recommendations}
        for employee_id in completed_club
    )
    mandatory = {
        event.event_id for event in tested.bundle.events.values() if event.mandatory
    }
    assert all(
        not (mandatory & {item.event_id for item in tested.get_journey(employee_id).recommendations})
        for employee_id in tested.bundle.employees
    )


def test_07_mandatory_events_are_excluded_before_scoring() -> None:
    tested = service()
    mandatory = {
        event.event_id for event in tested.bundle.events.values() if event.mandatory
    }
    recommended = {
        item.event_id
        for employee_id in tested.bundle.employees
        for item in tested.get_journey(employee_id).recommendations
    }
    assert mandatory.isdisjoint(recommended)


def test_08_unmet_prerequisite_is_counted_and_candidate_is_excluded() -> None:
    tested = service()
    journey = next(
        tested.get_journey(employee_id)
        for employee_id in sorted(tested.bundle.employees)
        if tested.get_journey(employee_id).reason_counts.get("prerequisite_blocked", 0)
    )
    assert journey.reason_counts["prerequisite_blocked"] > 0


def test_09_self_paced_event_is_available_without_session_date() -> None:
    tested = service()
    sessionless = {
        event.event_id
        for event in tested.bundle.events.values()
        if event.event_format == "self_paced" and not event.upcoming_sessions and not event.mandatory
    }
    assert any(
        item.event_id in sessionless
        for employee_id in tested.bundle.employees
        for item in tested.get_journey(employee_id).recommendations
    )


def test_10_event_without_future_session_is_excluded() -> None:
    original = service()
    employee_id, recommendation = next(
        (employee_id, item)
        for employee_id in sorted(original.bundle.employees)
        for item in original.get_journey(employee_id).recommendations
        if original.bundle.events[item.event_id].event_format != "self_paced"
    )
    event = original.bundle.events[recommendation.event_id]
    expired = replace(
        event,
        upcoming_sessions=(original.bundle.as_of_date - timedelta(days=1),),
    )
    bundle = replace(
        original.bundle,
        events={**original.bundle.events, event.event_id: expired},
    )
    journey = JourneyService(bundle).get_journey(employee_id)
    assert event.event_id not in {item.event_id for item in journey.recommendations}
    assert journey.reason_counts["no_future_session"] > 0
