import csv
import json
from datetime import date
from pathlib import Path
from typing import Any, cast

from app.domain.models import (
    ActivityRecord,
    CareerGoal,
    DatasetBundle,
    DevelopmentEvent,
    Employee,
    Grade,
    RoleProfile,
    Skill,
    SkillGain,
)

GRADES = {"Junior", "Middle", "Senior", "Lead"}


class DatasetError(ValueError):
    pass


def repository_dataset_dir() -> Path:
    return Path(__file__).resolve().parents[4] / "data" / "seed" / "career_quest_dataset"


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return cast(dict[str, Any], json.load(handle))


def _grade(value: str) -> Grade:
    if value not in GRADES:
        raise DatasetError(f"Unsupported grade: {value}")
    return cast(Grade, value)


def load_dataset(dataset_dir: Path | None = None) -> DatasetBundle:
    root = dataset_dir or repository_dataset_dir()
    skills_doc = _read_json(root / "skills.json")
    employees_doc = _read_json(root / "employees.json")
    events_doc = _read_json(root / "events.json")

    metadata = [skills_doc["meta"], employees_doc["meta"], events_doc["meta"]]
    signatures = {(item["dataset"], item["version"], item["as_of_date"]) for item in metadata}
    if len(signatures) != 1:
        raise DatasetError("JSON metadata does not describe one dataset snapshot")
    _, version, as_of_value = signatures.pop()

    skills = {
        item["skill_id"]: Skill(
            skill_id=item["skill_id"],
            name=item["name"],
            skill_type=item["type"],
            category=item["category"],
        )
        for item in skills_doc["skills"]
    }

    profiles: dict[tuple[str, Grade], RoleProfile] = {}
    for item in skills_doc["role_profiles"]:
        grade = _grade(item["grade"])
        profile = RoleProfile(
            role=item["role"],
            grade=grade,
            required_skills={key: int(value) for key, value in item["required_skills"].items()},
            critical_skills=frozenset(item["critical_skills"]),
        )
        profiles[(profile.role, grade)] = profile

    employees: dict[str, Employee] = {}
    for item in employees_doc["employees"]:
        goal_data = item.get("career_goal")
        goal = None
        if goal_data:
            goal = CareerGoal(
                target_role=goal_data["target_role"],
                target_grade=_grade(goal_data["target_grade"]),
            )
        employee = Employee(
            employee_id=item["employee_id"],
            full_name=item["full_name"],
            department=item["department"],
            role=item["role"],
            grade=_grade(item["grade"]),
            work_format=item["work_format"],
            preferred_language=item["preferred_language"],
            career_goal=goal,
            skills={key: int(value) for key, value in item["skills"].items()},
            last_review_date=date.fromisoformat(item["last_review_date"]),
        )
        employees[employee.employee_id] = employee

    events: dict[str, DevelopmentEvent] = {}
    for item in events_doc["events"]:
        event = DevelopmentEvent(
            event_id=item["event_id"],
            title=item["title"],
            event_type=item["type"],
            event_format=item["format"],
            duration_hours=float(item["duration_hours"]),
            mandatory=bool(item["mandatory"]),
            repeatable=bool(item.get("repeatable", False)),
            target_roles=frozenset(item["target_roles"]),
            target_grades=frozenset(_grade(value) for value in item["target_grades"]),
            develops_skills=tuple(
                SkillGain(
                    skill_id=gain["skill_id"],
                    gain=int(gain["gain"]),
                    max_level=int(gain["max_level"]),
                )
                for gain in item["develops_skills"]
            ),
            prerequisites={key: int(value) for key, value in item["prerequisites"].items()},
            upcoming_sessions=tuple(date.fromisoformat(value) for value in item["upcoming_sessions"]),
        )
        events[event.event_id] = event

    history: list[ActivityRecord] = []
    record_ids: set[str] = set()
    with (root / "activity_history.csv").open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            record_id = row["record_id"]
            if record_id in record_ids:
                raise DatasetError(f"Duplicate record_id: {record_id}")
            record_ids.add(record_id)
            history.append(
                ActivityRecord(
                    record_id=record_id,
                    employee_id=row["employee_id"],
                    event_id=row["event_id"],
                    activity_date=date.fromisoformat(row["date"]),
                    status=cast(Any, row["status"]),
                    completion_pct=int(row["completion_pct"]),
                    assigned_by=row["assigned_by"],
                )
            )

    return DatasetBundle(
        dataset_version=str(version),
        as_of_date=date.fromisoformat(str(as_of_value)),
        employees=employees,
        skills=skills,
        role_profiles=profiles,
        events=events,
        history=tuple(history),
    )
