import csv
import hashlib
import io
import json
import threading
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, cast

from app.domain.models import ActivityRecord, CareerGoal, DatasetBundle, Employee, Grade
from app.infrastructure.sqlite_repository import SQLiteRepository, StoredApplyResult

CSV_COLUMNS = (
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
STATUSES = {"completed", "in_progress", "dropped", "no_show", "declined", "overdue"}
ASSIGNED_BY = {"self", "manager", "hr"}
GRADES = {"Junior", "Middle", "Senior", "Lead"}


@dataclass(frozen=True)
class ValidationIssue:
    file: str
    location: str
    code: str
    reason: str


@dataclass(frozen=True)
class ImportValidationResult:
    valid: bool
    validation_token: str | None
    package_hash: str | None
    expires_at: datetime | None
    counts: dict[str, int]
    preview: dict[str, int]
    errors: tuple[ValidationIssue, ...]
    warnings: tuple[ValidationIssue, ...] = ()


class ImportError(RuntimeError):
    pass


class ValidationTokenError(ImportError):
    pass


class ImportConflict(ImportError):
    pass


class ImportService:
    def __init__(
        self,
        bundle: DatasetBundle,
        repository: SQLiteRepository,
        token_ttl: timedelta = timedelta(minutes=15),
    ):
        self.bundle = bundle
        self.repository = repository
        self.token_ttl = token_ttl
        self._activation_lock = threading.RLock()

    def validate(
        self,
        employees_document: dict[str, Any],
        activity_history_csv: str | None = None,
        now: datetime | None = None,
    ) -> ImportValidationResult:
        current_time = now or datetime.now(timezone.utc)
        errors: list[ValidationIssue] = []
        employees = self._validate_employees(employees_document, errors)
        history = self._validate_history(activity_history_csv, employees, errors)
        counts = {"employees": len(employees), "activity_history": len(history)}
        preview = self._preview(employees, history)
        if errors:
            return ImportValidationResult(
                valid=False,
                validation_token=None,
                package_hash=None,
                expires_at=None,
                counts=counts,
                preview=preview,
                errors=tuple(errors),
            )

        seed_record_ids = {record.record_id for record in self.bundle.history}
        payload = {
            "employees": employees,
            "history": history,
            "apply_employees": [
                item for item in employees if item.get("employee_id") not in self.bundle.employees
            ],
            "apply_history": [
                item for item in history if item.get("record_id") not in seed_record_ids
            ],
            "seed_no_op_employees": sum(
                item.get("employee_id") in self.bundle.employees for item in employees
            ),
            "seed_no_op_history": sum(
                item.get("record_id") in seed_record_ids for item in history
            ),
        }
        # Hash only the canonical uploaded content. Derived insert/no-op actions may
        # change after an earlier apply and must not change package identity.
        package_hash = self._canonical_hash(
            {"employees": employees, "history": history}
        )
        token = uuid.uuid4().hex
        expires_at = current_time + self.token_ttl
        self.repository.save_validation(token, package_hash, payload, preview, expires_at)
        return ImportValidationResult(
            valid=True,
            validation_token=token,
            package_hash=package_hash,
            expires_at=expires_at,
            counts=counts,
            preview=preview,
            errors=(),
        )

    def apply(
        self,
        validation_token: str,
        package_hash: str,
        idempotency_key: str,
        now: datetime | None = None,
    ) -> StoredApplyResult:
        if not idempotency_key.strip():
            raise ImportConflict("Idempotency-Key is required")
        validation = self.repository.get_validation(validation_token)
        if validation is None:
            raise ValidationTokenError("validation_token is unknown")
        current_time = now or datetime.now(timezone.utc)
        if validation.expires_at <= current_time:
            raise ValidationTokenError("validation_token expired")
        if not package_hash or package_hash != validation.package_hash:
            raise ValidationTokenError("package hash changed after validation")
        try:
            result = self.repository.apply_import(validation, idempotency_key, current_time)
            with self._activation_lock:
                activate_imported_records(
                    self.bundle,
                    validation.payload.get("apply_employees", []),
                    validation.payload.get("apply_history", []),
                )
            return result
        except ValueError as error:
            message = str(error)
            if "expired" in message:
                raise ValidationTokenError(message) from error
            raise ImportConflict(message) from error

    @staticmethod
    def _canonical_hash(payload: dict[str, Any]) -> str:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _validate_employees(
        self,
        document: dict[str, Any],
        errors: list[ValidationIssue],
    ) -> list[dict[str, Any]]:
        if not isinstance(document, dict):
            self._error(errors, "employees.json", "$", "invalid_json", "Expected JSON object")
            return []
        meta = document.get("meta")
        items = document.get("employees")
        if not isinstance(meta, dict):
            self._error(errors, "employees.json", "$.meta", "required", "Missing meta object")
        else:
            expected = {
                "dataset": "Career Quest",
                "version": self.bundle.dataset_version,
                "as_of_date": self.bundle.as_of_date.isoformat(),
            }
            for field, value in expected.items():
                if str(meta.get(field, "")) != value:
                    self._error(
                        errors,
                        "employees.json",
                        f"$.meta.{field}",
                        "metadata_mismatch",
                        f"Expected {value!r}",
                    )
        if not isinstance(items, list):
            self._error(
                errors, "employees.json", "$.employees", "required", "Expected employees array"
            )
            return []

        required = (
            "employee_id",
            "full_name",
            "department",
            "role",
            "grade",
            "work_format",
            "preferred_language",
            "skills",
            "last_review_date",
        )
        seen: set[str] = set()
        parsed: list[dict[str, Any]] = []
        for index, raw in enumerate(items):
            location = f"$.employees[{index}]"
            if not isinstance(raw, dict):
                self._error(errors, "employees.json", location, "invalid_type", "Expected object")
                continue
            for field in required:
                if field not in raw:
                    self._error(
                        errors,
                        "employees.json",
                        f"{location}.{field}",
                        "required",
                        "Required field is missing",
                    )
            employee_id = str(raw.get("employee_id", "")).strip()
            if not employee_id:
                self._error(errors, "employees.json", f"{location}.employee_id", "required", "ID is empty")
            elif employee_id in seen:
                self._error(
                    errors,
                    "employees.json",
                    f"{location}.employee_id",
                    "duplicate_id",
                    f"Duplicate employee_id {employee_id}",
                )
            seen.add(employee_id)

            grade = raw.get("grade")
            role = raw.get("role")
            if grade not in GRADES:
                self._error(errors, "employees.json", f"{location}.grade", "invalid_grade", "Unsupported grade")
            elif (role, grade) not in self.bundle.role_profiles:
                self._error(
                    errors,
                    "employees.json",
                    f"{location}.role",
                    "unknown_profile",
                    f"No role profile for {role} {grade}",
                )
            goal = raw.get("career_goal")
            if goal is not None:
                if not isinstance(goal, dict) or (
                    goal.get("target_role"), goal.get("target_grade")
                ) not in self.bundle.role_profiles:
                    self._error(
                        errors,
                        "employees.json",
                        f"{location}.career_goal",
                        "unknown_profile",
                        "Career goal has no role profile",
                    )
            skills = raw.get("skills")
            if not isinstance(skills, dict):
                self._error(errors, "employees.json", f"{location}.skills", "invalid_type", "Expected object")
            else:
                for skill_id, level in skills.items():
                    if skill_id not in self.bundle.skills:
                        self._error(
                            errors,
                            "employees.json",
                            f"{location}.skills.{skill_id}",
                            "unknown_skill_id",
                            f"Unknown skill_id {skill_id}",
                        )
                    if not isinstance(level, int) or isinstance(level, bool) or not 0 <= level <= 5:
                        self._error(
                            errors,
                            "employees.json",
                            f"{location}.skills.{skill_id}",
                            "out_of_range",
                            "Skill level must be an integer from 0 to 5",
                        )
            self._date_not_after_snapshot(
                raw.get("last_review_date"),
                "employees.json",
                f"{location}.last_review_date",
                errors,
            )
            if "hire_date" in raw:
                self._date_not_after_snapshot(
                    raw.get("hire_date"),
                    "employees.json",
                    f"{location}.hire_date",
                    errors,
                )
            parsed.append(raw)

        known_ids = set(self.bundle.employees) | seen
        for index, raw in enumerate(parsed):
            manager_id = raw.get("manager_id")
            if manager_id and manager_id not in known_ids:
                self._error(
                    errors,
                    "employees.json",
                    f"$.employees[{index}].manager_id",
                    "unknown_employee_id",
                    f"Unknown manager_id {manager_id}",
                )
            existing = self.bundle.employees.get(str(raw.get("employee_id", "")))
            if existing is not None and not self._equivalent_employee(existing, raw):
                self._error(
                    errors,
                    "employees.json",
                    f"$.employees[{index}].employee_id",
                    "conflict",
                    "employee_id exists with different content",
                )
        return sorted(parsed, key=lambda item: str(item.get("employee_id", "")))

    def _validate_history(
        self,
        content: str | None,
        imported_employees: list[dict[str, Any]],
        errors: list[ValidationIssue],
    ) -> list[dict[str, Any]]:
        if content is None or not content.strip():
            return []
        try:
            reader = csv.DictReader(io.StringIO(content, newline=""))
        except (csv.Error, UnicodeError) as error:
            self._error(errors, "activity_history.csv", "row 1", "invalid_csv", str(error))
            return []
        if tuple(reader.fieldnames or ()) != CSV_COLUMNS:
            self._error(
                errors,
                "activity_history.csv",
                "row 1",
                "invalid_columns",
                "Expected columns: " + ",".join(CSV_COLUMNS),
            )
            return []
        imported_ids = {str(item.get("employee_id")) for item in imported_employees}
        persisted_ids = {
            str(item.get("employee_id"))
            for item in self.repository.list_imported_employees()
        }
        known_employees = set(self.bundle.employees) | imported_ids | persisted_ids
        seed_records = {record.record_id: record for record in self.bundle.history}
        seen: set[str] = set()
        rows: list[dict[str, Any]] = []
        try:
            for row_number, row in enumerate(reader, start=2):
                record_id = (row.get("record_id") or "").strip()
                if not record_id:
                    self._error(errors, "activity_history.csv", f"row {row_number}, record_id", "required", "ID is empty")
                elif record_id in seen:
                    self._error(errors, "activity_history.csv", f"row {row_number}, record_id", "duplicate_id", f"Duplicate record_id {record_id}")
                seen.add(record_id)
                employee_id = (row.get("employee_id") or "").strip()
                event_id = (row.get("event_id") or "").strip()
                if employee_id not in known_employees:
                    self._error(errors, "activity_history.csv", f"row {row_number}, employee_id", "unknown_employee_id", f"Unknown employee_id {employee_id}")
                if event_id not in self.bundle.events:
                    self._error(errors, "activity_history.csv", f"row {row_number}, event_id", "unknown_event_id", f"Unknown event_id {event_id}")
                status = (row.get("status") or "").strip()
                if status not in STATUSES:
                    self._error(errors, "activity_history.csv", f"row {row_number}, status", "invalid_status", f"Unsupported status {status}")
                try:
                    completion_pct = int(row.get("completion_pct") or "")
                    if not 0 <= completion_pct <= 100:
                        raise ValueError
                    if status == "completed" and completion_pct != 100:
                        self._error(errors, "activity_history.csv", f"row {row_number}, completion_pct", "status_mismatch", "completed requires 100")
                    if status in {"declined", "no_show"} and completion_pct != 0:
                        self._error(errors, "activity_history.csv", f"row {row_number}, completion_pct", "status_mismatch", f"{status} requires 0")
                except ValueError:
                    self._error(errors, "activity_history.csv", f"row {row_number}, completion_pct", "out_of_range", "Expected integer from 0 to 100")
                self._date_not_after_snapshot(
                    row.get("date"),
                    "activity_history.csv",
                    f"row {row_number}, date",
                    errors,
                )
                due_date = (row.get("due_date") or "").strip()
                if due_date:
                    self._parse_date(due_date, "activity_history.csv", f"row {row_number}, due_date", errors)
                assigned_by = (row.get("assigned_by") or "").strip()
                if assigned_by not in ASSIGNED_BY:
                    self._error(errors, "activity_history.csv", f"row {row_number}, assigned_by", "invalid_value", f"Unsupported assigned_by {assigned_by}")
                existing = seed_records.get(record_id)
                if existing is not None and not self._equivalent_record(existing, row):
                    self._error(errors, "activity_history.csv", f"row {row_number}, record_id", "conflict", "record_id exists with different content")
                rows.append(dict(row))
        except (csv.Error, UnicodeError) as error:
            self._error(errors, "activity_history.csv", "row unknown", "invalid_csv", str(error))
        return sorted(rows, key=lambda item: item.get("record_id", ""))

    def _preview(
        self, employees: list[dict[str, Any]], history: list[dict[str, Any]]
    ) -> dict[str, int]:
        imported_employee_ids = {
            item["employee_id"] for item in self.repository.list_imported_employees()
        }
        imported_record_ids = {
            item["record_id"] for item in self.repository.list_imported_history()
        }
        return {
            "insert_employees": sum(
                item.get("employee_id") not in self.bundle.employees
                and item.get("employee_id") not in imported_employee_ids
                for item in employees
            ),
            "no_op_employees": sum(
                item.get("employee_id") in self.bundle.employees
                or item.get("employee_id") in imported_employee_ids
                for item in employees
            ),
            "insert_history": sum(
                item.get("record_id") not in {record.record_id for record in self.bundle.history}
                and item.get("record_id") not in imported_record_ids
                for item in history
            ),
            "no_op_history": sum(
                item.get("record_id") in {record.record_id for record in self.bundle.history}
                or item.get("record_id") in imported_record_ids
                for item in history
            ),
            "update": 0,
        }

    def _date_not_after_snapshot(
        self,
        value: Any,
        file: str,
        location: str,
        errors: list[ValidationIssue],
    ) -> None:
        parsed = self._parse_date(value, file, location, errors)
        if parsed is not None and parsed > self.bundle.as_of_date:
            self._error(errors, file, location, "future_date", "Date is after meta.as_of_date")

    @staticmethod
    def _parse_date(
        value: Any,
        file: str,
        location: str,
        errors: list[ValidationIssue],
    ) -> date | None:
        try:
            return date.fromisoformat(str(value))
        except (TypeError, ValueError):
            ImportService._error(errors, file, location, "invalid_date", "Expected ISO date YYYY-MM-DD")
            return None

    @staticmethod
    def _equivalent_employee(existing: Employee, raw: dict[str, Any]) -> bool:
        goal = raw.get("career_goal")
        existing_goal = (
            None
            if existing.career_goal is None
            else {
                "target_role": existing.career_goal.target_role,
                "target_grade": existing.career_goal.target_grade,
            }
        )
        return (
            raw.get("full_name") == existing.full_name
            and raw.get("department") == existing.department
            and raw.get("role") == existing.role
            and raw.get("grade") == existing.grade
            and raw.get("work_format") == existing.work_format
            and raw.get("preferred_language") == existing.preferred_language
            and goal == existing_goal
            and raw.get("skills") == existing.skills
            and raw.get("last_review_date") == existing.last_review_date.isoformat()
        )

    @staticmethod
    def _equivalent_record(existing: Any, row: dict[str, Any]) -> bool:
        return (
            row.get("employee_id") == existing.employee_id
            and row.get("event_id") == existing.event_id
            and row.get("date") == existing.activity_date.isoformat()
            and row.get("status") == existing.status
            and row.get("completion_pct") == str(existing.completion_pct)
            and row.get("assigned_by") == existing.assigned_by
        )

    @staticmethod
    def _error(
        errors: list[ValidationIssue],
        file: str,
        location: str,
        code: str,
        reason: str,
    ) -> None:
        errors.append(ValidationIssue(file=file, location=location, code=code, reason=reason))


def activate_imported_records(
    bundle: DatasetBundle,
    employees: list[dict[str, Any]],
    history: list[dict[str, Any]],
) -> None:
    """Merge committed import rows into the active immutable-seed overlay."""
    for item in employees:
        employee_id = str(item["employee_id"])
        if employee_id in bundle.employees:
            continue
        goal_data = item.get("career_goal")
        goal = None
        if isinstance(goal_data, dict):
            goal = CareerGoal(
                target_role=str(goal_data["target_role"]),
                target_grade=cast(Grade, goal_data["target_grade"]),
            )
        bundle.employees[employee_id] = Employee(
            employee_id=employee_id,
            full_name=str(item["full_name"]),
            department=str(item["department"]),
            role=str(item["role"]),
            grade=cast(Grade, item["grade"]),
            work_format=str(item["work_format"]),
            preferred_language=str(item["preferred_language"]),
            career_goal=goal,
            skills={str(key): int(value) for key, value in item["skills"].items()},
            last_review_date=date.fromisoformat(str(item["last_review_date"])),
        )

    existing_record_ids = {record.record_id for record in bundle.history}
    additions = []
    for item in history:
        record_id = str(item["record_id"])
        if record_id in existing_record_ids:
            continue
        additions.append(
            ActivityRecord(
                record_id=record_id,
                employee_id=str(item["employee_id"]),
                event_id=str(item["event_id"]),
                activity_date=date.fromisoformat(str(item["date"])),
                status=cast(Any, item["status"]),
                completion_pct=int(item["completion_pct"]),
                assigned_by=str(item["assigned_by"]),
                source="overlay",
            )
        )
        existing_record_ids.add(record_id)
    if additions:
        object.__setattr__(bundle, "history", (*bundle.history, *additions))
