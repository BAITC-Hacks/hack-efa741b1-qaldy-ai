import csv
import json
import math
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
ACTIVITY_STATUSES = {
    "completed",
    "in_progress",
    "dropped",
    "no_show",
    "declined",
    "overdue",
}
WORK_FORMATS = {"office", "hybrid", "remote"}
PREFERRED_LANGUAGES = {"kk", "ru", "en"}
EVENT_FORMATS = {"online", "offline", "self_paced"}
ASSIGNED_BY = {"self", "manager", "hr"}
REPEATABLE_EVENT_IDS = frozenset({"EV_036"})
ACTIVITY_HISTORY_HEADER = (
    "record_id",
    "employee_id",
    "event_id",
    "date",
    "due_date",
    "status",
    "completion_pct",
    "score",
    "feedback_rating",
    "assigned_by",
)


class DatasetError(ValueError):
    pass


def repository_dataset_dir() -> Path:
    for ancestor in Path(__file__).resolve().parents:
        candidate = ancestor / "data" / "seed" / "career_quest_dataset"
        if candidate.is_dir():
            return candidate
    raise DatasetError(
        "Seed dataset was not found in the source checkout; set DATASET_DIR explicitly"
    )


def _read_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, json.JSONDecodeError) as error:
        raise DatasetError(f"{path.name}: cannot read valid JSON: {error}") from error
    if not isinstance(document, dict):
        raise DatasetError(f"{path.name}: root must be an object")
    return cast(dict[str, Any], document)


def _object(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise DatasetError(f"{context}: expected an object")
    return cast(dict[str, Any], value)


def _array(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise DatasetError(f"{context}: expected an array")
    return cast(list[Any], value)


def _text(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DatasetError(f"{context}: expected a non-empty string")
    return value


def _date(value: Any, context: str) -> date:
    raw = _text(value, context)
    try:
        return date.fromisoformat(raw)
    except ValueError as error:
        raise DatasetError(f"{context}: expected an ISO date, got {raw!r}") from error


def _grade(value: Any, context: str) -> Grade:
    raw = _text(value, context)
    if raw not in GRADES:
        raise DatasetError(f"{context}: unsupported grade {raw!r}")
    return cast(Grade, raw)


def _strict_bool(value: Any, context: str) -> bool:
    if type(value) is not bool:
        raise DatasetError(f"{context}: expected a boolean")
    return cast(bool, value)


def _choice(value: Any, allowed: set[str], context: str) -> str:
    parsed = _text(value, context)
    if parsed not in allowed:
        raise DatasetError(
            f"{context}: expected one of {sorted(allowed)!r}, got {parsed!r}"
        )
    return parsed


def _integer(value: Any, context: str) -> int:
    if type(value) is not int:
        raise DatasetError(f"{context}: expected an integer")
    return cast(int, value)


def _level(value: Any, context: str, *, minimum: int = 0) -> int:
    parsed = _integer(value, context)
    if not minimum <= parsed <= 5:
        raise DatasetError(f"{context}: expected a value in range {minimum}..5, got {parsed}")
    return parsed


def _number(value: Any, context: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DatasetError(f"{context}: expected a number")
    parsed = float(value)
    if not math.isfinite(parsed):
        raise DatasetError(f"{context}: expected a finite number")
    return parsed


def _unique(value: str, seen: set[str], label: str, context: str) -> None:
    if value in seen:
        raise DatasetError(f"{context}: duplicate {label} {value!r}")
    seen.add(value)


def _skill_levels(
    value: Any,
    context: str,
    skills: dict[str, Skill],
) -> dict[str, int]:
    result: dict[str, int] = {}
    for skill_id, raw_level in _object(value, context).items():
        item_context = f"{context}.{skill_id}"
        if skill_id not in skills:
            raise DatasetError(f"{item_context}: unknown skill_id {skill_id!r}")
        result[skill_id] = _level(raw_level, item_context)
    return result


def _metadata(
    documents: tuple[tuple[str, dict[str, Any]], ...],
) -> tuple[str, date]:
    signatures: set[tuple[str, str, date]] = set()
    for filename, document in documents:
        meta = _object(document.get("meta"), f"{filename}.meta")
        signatures.add(
            (
                _text(meta.get("dataset"), f"{filename}.meta.dataset"),
                _text(meta.get("version"), f"{filename}.meta.version"),
                _date(meta.get("as_of_date"), f"{filename}.meta.as_of_date"),
            )
        )
    if len(signatures) != 1:
        raise DatasetError("JSON metadata does not describe one dataset snapshot")
    _, version, as_of_date = signatures.pop()
    return version, as_of_date


def _csv_int(value: str, context: str) -> int:
    try:
        return int(value)
    except ValueError as error:
        raise DatasetError(f"{context}: expected an integer, got {value!r}") from error


def _csv_float(value: str, context: str) -> float:
    try:
        result = float(value)
    except ValueError as error:
        raise DatasetError(f"{context}: expected a number, got {value!r}") from error
    if not math.isfinite(result):
        raise DatasetError(f"{context}: expected a finite number")
    return result


def load_dataset(dataset_dir: Path | None = None) -> DatasetBundle:
    root = dataset_dir or repository_dataset_dir()
    skills_doc = _read_json(root / "skills.json")
    employees_doc = _read_json(root / "employees.json")
    events_doc = _read_json(root / "events.json")
    version, as_of_date = _metadata(
        (
            ("skills.json", skills_doc),
            ("employees.json", employees_doc),
            ("events.json", events_doc),
        )
    )

    skills: dict[str, Skill] = {}
    seen_skill_ids: set[str] = set()
    for index, raw_item in enumerate(_array(skills_doc.get("skills"), "skills.json.skills")):
        context = f"skills.json.skills[{index}]"
        item = _object(raw_item, context)
        skill_id = _text(item.get("skill_id"), f"{context}.skill_id")
        _unique(skill_id, seen_skill_ids, "skill_id", context)
        skills[skill_id] = Skill(
            skill_id=skill_id,
            name=_text(item.get("name"), f"{context}.name"),
            skill_type=_text(item.get("type"), f"{context}.type"),
            category=_text(item.get("category"), f"{context}.category"),
        )

    profiles: dict[tuple[str, Grade], RoleProfile] = {}
    for index, raw_item in enumerate(
        _array(skills_doc.get("role_profiles"), "skills.json.role_profiles")
    ):
        context = f"skills.json.role_profiles[{index}]"
        item = _object(raw_item, context)
        role = _text(item.get("role"), f"{context}.role")
        grade = _grade(item.get("grade"), f"{context}.grade")
        profile_id = (role, grade)
        if profile_id in profiles:
            raise DatasetError(
                f"{context}: duplicate role profile for role={role!r}, grade={grade!r}"
            )
        required_skills = _skill_levels(
            item.get("required_skills"), f"{context}.required_skills", skills
        )
        critical_skills: set[str] = set()
        for skill_index, raw_skill_id in enumerate(
            _array(item.get("critical_skills"), f"{context}.critical_skills")
        ):
            skill_id = _text(raw_skill_id, f"{context}.critical_skills[{skill_index}]")
            if skill_id not in skills:
                raise DatasetError(
                    f"{context}.critical_skills[{skill_index}]: unknown skill_id {skill_id!r}"
                )
            critical_skills.add(skill_id)
        if not critical_skills.issubset(required_skills):
            raise DatasetError(
                f"{context}.critical_skills: every critical skill must also be required"
            )
        profiles[profile_id] = RoleProfile(
            role=role,
            grade=grade,
            required_skills=required_skills,
            critical_skills=frozenset(critical_skills),
        )

    employees: dict[str, Employee] = {}
    seen_employee_ids: set[str] = set()
    for index, raw_item in enumerate(
        _array(employees_doc.get("employees"), "employees.json.employees")
    ):
        context = f"employees.json.employees[{index}]"
        item = _object(raw_item, context)
        employee_id = _text(item.get("employee_id"), f"{context}.employee_id")
        _unique(employee_id, seen_employee_ids, "employee_id", context)
        role = _text(item.get("role"), f"{context}.role")
        grade = _grade(item.get("grade"), f"{context}.grade")
        if (role, grade) not in profiles:
            raise DatasetError(
                f"{context}: no role profile for role={role!r}, grade={grade!r}"
            )
        goal = None
        if item.get("career_goal") is not None:
            goal_context = f"{context}.career_goal"
            raw_goal = _object(item["career_goal"], goal_context)
            target_role = _text(raw_goal.get("target_role"), f"{goal_context}.target_role")
            target_grade = _grade(raw_goal.get("target_grade"), f"{goal_context}.target_grade")
            if (target_role, target_grade) not in profiles:
                raise DatasetError(
                    f"{goal_context}: no role profile for role={target_role!r}, "
                    f"grade={target_grade!r}"
                )
            goal = CareerGoal(target_role=target_role, target_grade=target_grade)
        last_review_date = _date(item.get("last_review_date"), f"{context}.last_review_date")
        if last_review_date > as_of_date:
            raise DatasetError(f"{context}.last_review_date: date is after snapshot {as_of_date}")
        manager_id = item.get("manager_id")
        if manager_id is not None:
            manager_id = _text(manager_id, f"{context}.manager_id")
        hire_date = (
            _date(item.get("hire_date"), f"{context}.hire_date")
            if item.get("hire_date") is not None
            else None
        )
        if hire_date is not None and hire_date > as_of_date:
            raise DatasetError(f"{context}.hire_date: date is after snapshot {as_of_date}")
        tenure_months = (
            _integer(item.get("tenure_months"), f"{context}.tenure_months")
            if item.get("tenure_months") is not None
            else None
        )
        if tenure_months is not None and tenure_months < 0:
            raise DatasetError(f"{context}.tenure_months: must be non-negative")
        employees[employee_id] = Employee(
            employee_id=employee_id,
            full_name=_text(item.get("full_name"), f"{context}.full_name"),
            department=_text(item.get("department"), f"{context}.department"),
            role=role,
            grade=grade,
            work_format=_choice(
                item.get("work_format"), WORK_FORMATS, f"{context}.work_format"
            ),
            preferred_language=_choice(
                item.get("preferred_language"),
                PREFERRED_LANGUAGES,
                f"{context}.preferred_language",
            ),
            career_goal=goal,
            skills=_skill_levels(item.get("skills"), f"{context}.skills", skills),
            last_review_date=last_review_date,
            manager_id=cast(str | None, manager_id),
            hire_date=hire_date,
            tenure_months=tenure_months,
        )
    for employee in employees.values():
        if employee.manager_id is None:
            continue
        context = f"employees.json employee_id={employee.employee_id!r}.manager_id"
        if employee.manager_id == employee.employee_id:
            raise DatasetError(f"{context}: employee cannot manage themselves")
        if employee.manager_id not in employees:
            raise DatasetError(f"{context}: unknown employee_id {employee.manager_id!r}")
        manager = employees[employee.manager_id]
        if manager.grade != "Lead":
            raise DatasetError(f"{context}: manager must have Lead grade")
        if manager.department != employee.department:
            raise DatasetError(f"{context}: manager must belong to the same department")

    events: dict[str, DevelopmentEvent] = {}
    seen_event_ids: set[str] = set()
    for index, raw_item in enumerate(_array(events_doc.get("events"), "events.json.events")):
        context = f"events.json.events[{index}]"
        item = _object(raw_item, context)
        event_id = _text(item.get("event_id"), f"{context}.event_id")
        _unique(event_id, seen_event_ids, "event_id", context)
        target_roles = tuple(
            _text(value, f"{context}.target_roles[{target_index}]")
            for target_index, value in enumerate(
                _array(item.get("target_roles"), f"{context}.target_roles")
            )
        )
        target_grades = tuple(
            _grade(value, f"{context}.target_grades[{target_index}]")
            for target_index, value in enumerate(
                _array(item.get("target_grades"), f"{context}.target_grades")
            )
        )
        for target_role in target_roles:
            for target_grade in target_grades:
                if (target_role, target_grade) not in profiles:
                    raise DatasetError(
                        f"{context}: target role/grade has no profile: "
                        f"role={target_role!r}, grade={target_grade!r}"
                    )
        develops_skills: list[SkillGain] = []
        developed_ids: set[str] = set()
        for gain_index, raw_gain in enumerate(
            _array(item.get("develops_skills"), f"{context}.develops_skills")
        ):
            gain_context = f"{context}.develops_skills[{gain_index}]"
            gain = _object(raw_gain, gain_context)
            skill_id = _text(gain.get("skill_id"), f"{gain_context}.skill_id")
            if skill_id not in skills:
                raise DatasetError(f"{gain_context}.skill_id: unknown skill_id {skill_id!r}")
            _unique(skill_id, developed_ids, "skill_id", gain_context)
            develops_skills.append(
                SkillGain(
                    skill_id=skill_id,
                    gain=_level(gain.get("gain"), f"{gain_context}.gain", minimum=1),
                    max_level=_level(gain.get("max_level"), f"{gain_context}.max_level"),
                )
            )
        duration_hours = _number(item.get("duration_hours"), f"{context}.duration_hours")
        if duration_hours <= 0:
            raise DatasetError(f"{context}.duration_hours: must be greater than zero")
        repeatable = event_id in REPEATABLE_EVENT_IDS
        if "repeatable" in item:
            declared_repeatable = _strict_bool(
                item["repeatable"], f"{context}.repeatable"
            )
            if declared_repeatable != repeatable:
                raise DatasetError(
                    f"{context}.repeatable: conflicts with the dataset policy for "
                    f"{event_id!r}"
                )
        events[event_id] = DevelopmentEvent(
            event_id=event_id,
            title=_text(item.get("title"), f"{context}.title"),
            event_type=_text(item.get("type"), f"{context}.type"),
            event_format=_choice(
                item.get("format"), EVENT_FORMATS, f"{context}.format"
            ),
            duration_hours=duration_hours,
            mandatory=_strict_bool(item.get("mandatory"), f"{context}.mandatory"),
            repeatable=repeatable,
            target_roles=frozenset(target_roles),
            target_grades=frozenset(target_grades),
            develops_skills=tuple(develops_skills),
            prerequisites=_skill_levels(
                item.get("prerequisites"), f"{context}.prerequisites", skills
            ),
            upcoming_sessions=tuple(
                _date(value, f"{context}.upcoming_sessions[{session_index}]")
                for session_index, value in enumerate(
                    _array(item.get("upcoming_sessions"), f"{context}.upcoming_sessions")
                )
            ),
        )

    history: list[ActivityRecord] = []
    seen_record_ids: set[str] = set()
    history_path = root / "activity_history.csv"
    try:
        handle = history_path.open("r", encoding="utf-8", newline="")
    except OSError as error:
        raise DatasetError(f"activity_history.csv: cannot read file: {error}") from error
    with handle:
        reader = csv.DictReader(handle)
        actual_header = tuple(reader.fieldnames or ())
        if actual_header != ACTIVITY_HISTORY_HEADER:
            raise DatasetError(
                "activity_history.csv: expected exact header "
                f"{list(ACTIVITY_HISTORY_HEADER)!r}, got {list(actual_header)!r}"
            )
        for line_number, row in enumerate(reader, start=2):
            context = f"activity_history.csv row {line_number}"
            if None in row or any(value is None for value in row.values()):
                raise DatasetError(f"{context}: row does not match the declared header")
            record_id = _text(row["record_id"], f"{context}.record_id")
            _unique(record_id, seen_record_ids, "record_id", context)
            context += f" record_id={record_id!r}"
            employee_id = _text(row["employee_id"], f"{context}.employee_id")
            if employee_id not in employees:
                raise DatasetError(f"{context}.employee_id: unknown employee_id {employee_id!r}")
            event_id = _text(row["event_id"], f"{context}.event_id")
            if event_id not in events:
                raise DatasetError(f"{context}.event_id: unknown event_id {event_id!r}")
            activity_date = _date(row["date"], f"{context}.date")
            if activity_date > as_of_date:
                raise DatasetError(f"{context}.date: {activity_date} is after snapshot {as_of_date}")
            status = _text(row["status"], f"{context}.status")
            if status not in ACTIVITY_STATUSES:
                raise DatasetError(f"{context}.status: unsupported status {status!r}")
            completion_pct = _csv_int(row["completion_pct"], f"{context}.completion_pct")
            if not 0 <= completion_pct <= 100:
                raise DatasetError(
                    f"{context}.completion_pct: expected a value in range 0..100, "
                    f"got {completion_pct}"
                )
            if status == "completed" and completion_pct != 100:
                raise DatasetError(f"{context}.completion_pct: completed requires 100")
            if status in {"declined", "no_show"} and completion_pct != 0:
                raise DatasetError(f"{context}.completion_pct: {status} requires 0")
            if status == "in_progress" and not 0 <= completion_pct <= 95:
                raise DatasetError(
                    f"{context}.completion_pct: in_progress requires a value in range 0..95"
                )
            if status == "dropped" and not 5 <= completion_pct <= 95:
                raise DatasetError(
                    f"{context}.completion_pct: dropped requires a value in range 5..95"
                )
            if status == "overdue" and not 0 <= completion_pct <= 95:
                raise DatasetError(
                    f"{context}.completion_pct: overdue requires a value in range 0..95"
                )
            score = _csv_float(row["score"], f"{context}.score") if row["score"] else None
            if score is not None and not 0 <= score <= 100:
                raise DatasetError(
                    f"{context}.score: expected a value in range 0..100, got {score}"
                )
            feedback_rating = (
                _csv_int(row["feedback_rating"], f"{context}.feedback_rating")
                if row["feedback_rating"]
                else None
            )
            if feedback_rating is not None and not 1 <= feedback_rating <= 5:
                raise DatasetError(
                    f"{context}.feedback_rating: expected a value in range 1..5, "
                    f"got {feedback_rating}"
                )
            assigned_by = _choice(
                row["assigned_by"], ASSIGNED_BY, f"{context}.assigned_by"
            )
            due_date = (
                _date(row["due_date"], f"{context}.due_date")
                if row["due_date"]
                else None
            )
            event = events[event_id]
            if status == "no_show" and event.event_format == "self_paced":
                raise DatasetError(f"{context}.status: no_show requires a scheduled event")
            if status == "declined" and assigned_by == "self":
                raise DatasetError(
                    f"{context}.assigned_by: declined must be assigned by manager or hr"
                )
            if status == "overdue" and (not event.mandatory or due_date is None):
                raise DatasetError(
                    f"{context}.status: overdue requires a mandatory event and due_date"
                )
            history.append(
                ActivityRecord(
                    record_id=record_id,
                    employee_id=employee_id,
                    event_id=event_id,
                    activity_date=activity_date,
                    status=cast(Any, status),
                    completion_pct=completion_pct,
                    assigned_by=assigned_by,
                    due_date=due_date,
                    score=score,
                    feedback_rating=feedback_rating,
                )
            )

    return DatasetBundle(
        dataset_version=version,
        as_of_date=as_of_date,
        employees=employees,
        skills=skills,
        role_profiles=profiles,
        events=events,
        history=tuple(history),
    )
