import csv
import hashlib
import io
import json
import threading
import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
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
WORK_FORMATS = {"office", "hybrid", "remote"}
LANGUAGES = {"kk", "ru", "en"}
MAX_IMPORT_EMPLOYEES = 10_000
MAX_IMPORT_HISTORY_ROWS = 100_000


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
        if len(items) > MAX_IMPORT_EMPLOYEES:
            self._error(
                errors,
                "employees.json",
                "$.employees",
                "too_many_rows",
                f"At most {MAX_IMPORT_EMPLOYEES} employees are allowed per package",
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
            employee_id_value = raw.get("employee_id")
            employee_id = (
                employee_id_value.strip()
                if isinstance(employee_id_value, str)
                else ""
            )
            if employee_id_value is not None and not isinstance(employee_id_value, str):
                self._error(
                    errors,
                    "employees.json",
                    f"{location}.employee_id",
                    "invalid_type",
                    "Expected string",
                )
            elif not employee_id:
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

            for field in ("full_name", "department"):
                value = raw.get(field)
                if not isinstance(value, str):
                    self._error(
                        errors,
                        "employees.json",
                        f"{location}.{field}",
                        "invalid_type",
                        "Expected string",
                    )
                elif not value.strip():
                    self._error(
                        errors,
                        "employees.json",
                        f"{location}.{field}",
                        "required",
                        "Value is empty",
                    )

            work_format = raw.get("work_format")
            if not isinstance(work_format, str) or work_format not in WORK_FORMATS:
                self._error(
                    errors,
                    "employees.json",
                    f"{location}.work_format",
                    "invalid_value",
                    "Expected one of: " + ", ".join(sorted(WORK_FORMATS)),
                )
            preferred_language = raw.get("preferred_language")
            if (
                not isinstance(preferred_language, str)
                or preferred_language not in LANGUAGES
            ):
                self._error(
                    errors,
                    "employees.json",
                    f"{location}.preferred_language",
                    "invalid_value",
                    "Expected one of: " + ", ".join(sorted(LANGUAGES)),
                )

            grade = raw.get("grade")
            role = raw.get("role")
            role_is_string = isinstance(role, str)
            grade_is_string = isinstance(grade, str)
            if not role_is_string:
                self._error(
                    errors,
                    "employees.json",
                    f"{location}.role",
                    "invalid_type",
                    "Expected string",
                )
            if not grade_is_string:
                self._error(
                    errors,
                    "employees.json",
                    f"{location}.grade",
                    "invalid_type",
                    "Expected string",
                )
            elif grade not in GRADES:
                self._error(errors, "employees.json", f"{location}.grade", "invalid_grade", "Unsupported grade")
            if role_is_string and grade_is_string and grade in GRADES and (
                role, grade
            ) not in self.bundle.role_profiles:
                self._error(
                    errors,
                    "employees.json",
                    f"{location}.role",
                    "unknown_profile",
                    f"No role profile for {role} {grade}",
                )
            goal = raw.get("career_goal")
            if goal is not None:
                if not isinstance(goal, dict):
                    self._error(
                        errors,
                        "employees.json",
                        f"{location}.career_goal",
                        "invalid_type",
                        "Expected object or null",
                    )
                else:
                    target_role = goal.get("target_role")
                    target_grade = goal.get("target_grade")
                    target_role_is_string = isinstance(target_role, str)
                    target_grade_is_string = isinstance(target_grade, str)
                    if not target_role_is_string:
                        self._error(
                            errors,
                            "employees.json",
                            f"{location}.career_goal.target_role",
                            "invalid_type",
                            "Expected string",
                        )
                    if not target_grade_is_string:
                        self._error(
                            errors,
                            "employees.json",
                            f"{location}.career_goal.target_grade",
                            "invalid_type",
                            "Expected string",
                        )
                    elif target_grade not in GRADES:
                        self._error(
                            errors,
                            "employees.json",
                            f"{location}.career_goal.target_grade",
                            "invalid_grade",
                            "Unsupported grade",
                        )
                    if (
                        target_role_is_string
                        and target_grade_is_string
                        and target_grade in GRADES
                        and (target_role, target_grade) not in self.bundle.role_profiles
                    ):
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
            tenure_months = raw.get("tenure_months")
            if tenure_months is not None and (
                not isinstance(tenure_months, int)
                or isinstance(tenure_months, bool)
                or tenure_months < 0
            ):
                self._error(
                    errors,
                    "employees.json",
                    f"{location}.tenure_months",
                    "out_of_range",
                    "Expected a non-negative integer or null",
                )
            parsed.append(raw)

        known_ids = set(self.bundle.employees) | seen
        imported_by_id = {
            item.get("employee_id"): item
            for item in parsed
            if isinstance(item.get("employee_id"), str)
        }
        for index, raw in enumerate(parsed):
            manager_id = raw.get("manager_id")
            if manager_id is not None and not isinstance(manager_id, str):
                self._error(
                    errors,
                    "employees.json",
                    f"$.employees[{index}].manager_id",
                    "invalid_type",
                    "Expected string or null",
                )
            elif manager_id and manager_id not in known_ids:
                self._error(
                    errors,
                    "employees.json",
                    f"$.employees[{index}].manager_id",
                    "unknown_employee_id",
                    f"Unknown manager_id {manager_id}",
                )
            elif manager_id:
                manager = self.bundle.employees.get(manager_id)
                manager_grade = (
                    manager.grade
                    if manager is not None
                    else imported_by_id.get(manager_id, {}).get("grade")
                )
                manager_department = (
                    manager.department
                    if manager is not None
                    else imported_by_id.get(manager_id, {}).get("department")
                )
                if manager_grade != "Lead":
                    self._error(
                        errors,
                        "employees.json",
                        f"$.employees[{index}].manager_id",
                        "invalid_manager",
                        "Manager must have Lead grade",
                    )
                if manager_department != raw.get("department"):
                    self._error(
                        errors,
                        "employees.json",
                        f"$.employees[{index}].manager_id",
                        "invalid_manager",
                        "Manager must belong to the same department",
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
        persisted_records = {
            str(item.get("record_id")): item
            for item in self.repository.list_imported_history()
        }
        completed_non_repeatable: dict[
            tuple[str, str], dict[str, tuple[str, Any]]
        ] = {}
        for record in self.bundle.history:
            event = self.bundle.events.get(record.event_id)
            if record.status != "completed" or event is None or event.repeatable:
                continue
            completed_non_repeatable.setdefault(
                (record.employee_id, record.event_id), {}
            )[record.record_id] = ("seed", record)
        for persisted in persisted_records.values():
            event_id = str(persisted.get("event_id", ""))
            event = self.bundle.events.get(event_id)
            if (
                persisted.get("status") != "completed"
                or event is None
                or event.repeatable
            ):
                continue
            employee_id = str(persisted.get("employee_id", ""))
            record_id = str(persisted.get("record_id", ""))
            completed_non_repeatable.setdefault((employee_id, event_id), {})[
                record_id
            ] = ("persisted", persisted)
        seen: set[str] = set()
        rows: list[dict[str, Any]] = []
        try:
            for row_number, row in enumerate(reader, start=2):
                if row_number > MAX_IMPORT_HISTORY_ROWS + 1:
                    self._error(
                        errors,
                        "activity_history.csv",
                        f"row {row_number}",
                        "too_many_rows",
                        f"At most {MAX_IMPORT_HISTORY_ROWS} history rows are allowed per package",
                    )
                    break
                if None in row:
                    self._error(
                        errors,
                        "activity_history.csv",
                        f"row {row_number}",
                        "invalid_columns",
                        "Row has more values than the declared columns",
                    )
                canonical_row = {
                    column: row.get(column) or "" for column in CSV_COLUMNS
                }
                record_id = canonical_row["record_id"].strip()
                if not record_id:
                    self._error(errors, "activity_history.csv", f"row {row_number}, record_id", "required", "ID is empty")
                elif record_id in seen:
                    self._error(errors, "activity_history.csv", f"row {row_number}, record_id", "duplicate_id", f"Duplicate record_id {record_id}")
                seen.add(record_id)
                employee_id = canonical_row["employee_id"].strip()
                event_id = canonical_row["event_id"].strip()
                if employee_id not in known_employees:
                    self._error(errors, "activity_history.csv", f"row {row_number}, employee_id", "unknown_employee_id", f"Unknown employee_id {employee_id}")
                if event_id not in self.bundle.events:
                    self._error(errors, "activity_history.csv", f"row {row_number}, event_id", "unknown_event_id", f"Unknown event_id {event_id}")
                status = canonical_row["status"].strip()
                if status not in STATUSES:
                    self._error(errors, "activity_history.csv", f"row {row_number}, status", "invalid_status", f"Unsupported status {status}")
                completion_pct: int | None = None
                try:
                    completion_pct = int(canonical_row["completion_pct"])
                    if not 0 <= completion_pct <= 100:
                        raise ValueError
                except ValueError:
                    self._error(errors, "activity_history.csv", f"row {row_number}, completion_pct", "out_of_range", "Expected integer from 0 to 100")
                if completion_pct is not None and status in STATUSES:
                    self._validate_status_completion(
                        status, completion_pct, row_number, errors
                    )
                self._validate_optional_score(
                    canonical_row["score"], row_number, errors
                )
                self._validate_optional_feedback_rating(
                    canonical_row["feedback_rating"], row_number, errors
                )
                self._date_not_after_snapshot(
                    canonical_row["date"],
                    "activity_history.csv",
                    f"row {row_number}, date",
                    errors,
                )
                due_date = canonical_row["due_date"].strip()
                if due_date:
                    self._parse_date(due_date, "activity_history.csv", f"row {row_number}, due_date", errors)
                assigned_by = canonical_row["assigned_by"].strip()
                if assigned_by not in ASSIGNED_BY:
                    self._error(errors, "activity_history.csv", f"row {row_number}, assigned_by", "invalid_value", f"Unsupported assigned_by {assigned_by}")
                existing = seed_records.get(record_id)
                record_conflict = existing is not None and not self._equivalent_record(
                    existing, canonical_row
                )
                persisted = persisted_records.get(record_id)
                if persisted is not None and not self._equivalent_imported_record(
                    persisted, canonical_row
                ):
                    record_conflict = True
                if record_conflict:
                    self._error(errors, "activity_history.csv", f"row {row_number}, record_id", "conflict", "record_id exists with different content")
                event = self.bundle.events.get(event_id)
                if (
                    record_id
                    and status == "completed"
                    and event is not None
                    and not event.repeatable
                ):
                    pair = (employee_id, event_id)
                    completions = completed_non_repeatable.setdefault(pair, {})
                    conflicting_ids = [
                        existing_id
                        for existing_id in completions
                        if existing_id != record_id
                    ]
                    if conflicting_ids:
                        self._error(
                            errors,
                            "activity_history.csv",
                            f"row {row_number}, event_id",
                            "non_repeatable_completion",
                            "Non-repeatable event is already completed for this employee "
                            f"by record {sorted(conflicting_ids)[0]}",
                        )
                    elif record_id not in completions:
                        completions[record_id] = ("upload", canonical_row)
                rows.append(canonical_row)
        except (csv.Error, UnicodeError) as error:
            self._error(errors, "activity_history.csv", "row unknown", "invalid_csv", str(error))
        return sorted(rows, key=lambda item: item.get("record_id", ""))

    @staticmethod
    def _validate_optional_score(
        value: str,
        row_number: int,
        errors: list[ValidationIssue],
    ) -> None:
        stripped = value.strip()
        if not stripped:
            return
        try:
            score = Decimal(stripped)
            if not score.is_finite() or not Decimal("0") <= score <= Decimal("100"):
                raise InvalidOperation
        except InvalidOperation:
            ImportService._error(
                errors,
                "activity_history.csv",
                f"row {row_number}, score",
                "out_of_range",
                "Expected a number from 0 to 100 or an empty value",
            )

    @staticmethod
    def _validate_optional_feedback_rating(
        value: str,
        row_number: int,
        errors: list[ValidationIssue],
    ) -> None:
        stripped = value.strip()
        if not stripped:
            return
        try:
            rating = int(stripped)
            if not 1 <= rating <= 5:
                raise ValueError
        except ValueError:
            ImportService._error(
                errors,
                "activity_history.csv",
                f"row {row_number}, feedback_rating",
                "out_of_range",
                "Expected an integer from 1 to 5 or an empty value",
            )

    @staticmethod
    def _validate_status_completion(
        status: str,
        completion_pct: int,
        row_number: int,
        errors: list[ValidationIssue],
    ) -> None:
        reason: str | None = None
        if status == "completed" and completion_pct != 100:
            reason = "completed requires 100"
        elif status in {"declined", "no_show"} and completion_pct != 0:
            reason = f"{status} requires 0"
        elif status in {"in_progress", "dropped"} and not 1 <= completion_pct <= 99:
            reason = f"{status} requires a value from 1 to 99"
        elif status == "overdue" and completion_pct == 100:
            reason = "overdue requires a value below 100"
        if reason is not None:
            ImportService._error(
                errors,
                "activity_history.csv",
                f"row {row_number}, completion_pct",
                "status_mismatch",
                reason,
            )

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
        manager_matches = "manager_id" not in raw or (
            raw.get("manager_id") or None
        ) == existing.manager_id
        hire_date_matches = "hire_date" not in raw or (
            raw.get("hire_date") or ""
        ) == (existing.hire_date.isoformat() if existing.hire_date else "")
        tenure_matches = (
            "tenure_months" not in raw
            or raw.get("tenure_months") == existing.tenure_months
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
            and manager_matches
            and hire_date_matches
            and tenure_matches
        )

    @staticmethod
    def _equivalent_record(existing: Any, row: dict[str, Any]) -> bool:
        due_date = (row.get("due_date") or "").strip()
        existing_due_date = (
            existing.due_date.isoformat() if existing.due_date is not None else ""
        )
        score = (row.get("score") or "").strip()
        try:
            score_matches = (
                not score and existing.score is None
            ) or (
                bool(score)
                and existing.score is not None
                and Decimal(score) == Decimal(str(existing.score))
            )
        except InvalidOperation:
            score_matches = False
        feedback_rating = (row.get("feedback_rating") or "").strip()
        try:
            feedback_matches = (
                not feedback_rating and existing.feedback_rating is None
            ) or (
                bool(feedback_rating)
                and existing.feedback_rating is not None
                and int(feedback_rating) == existing.feedback_rating
            )
        except ValueError:
            feedback_matches = False
        return (
            row.get("employee_id") == existing.employee_id
            and row.get("event_id") == existing.event_id
            and row.get("date") == existing.activity_date.isoformat()
            and due_date == existing_due_date
            and row.get("status") == existing.status
            and row.get("completion_pct") == str(existing.completion_pct)
            and score_matches
            and feedback_matches
            and row.get("assigned_by") == existing.assigned_by
        )

    @staticmethod
    def _equivalent_imported_record(
        existing: dict[str, Any], row: dict[str, Any]
    ) -> bool:
        return all(
            (existing.get(column) or "") == (row.get(column) or "")
            for column in CSV_COLUMNS
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
        hire_date_value = item.get("hire_date")
        tenure_months_value = item.get("tenure_months")
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
            manager_id=(
                str(item["manager_id"])
                if item.get("manager_id") not in (None, "")
                else None
            ),
            hire_date=(
                date.fromisoformat(str(hire_date_value))
                if hire_date_value not in (None, "")
                else None
            ),
            tenure_months=(
                int(tenure_months_value)
                if tenure_months_value is not None
                else None
            ),
        )

    existing_record_ids = {record.record_id for record in bundle.history}
    additions = []
    for item in history:
        record_id = str(item["record_id"])
        if record_id in existing_record_ids:
            continue
        due_date_value = str(item.get("due_date") or "").strip()
        score_value = str(item.get("score") or "").strip()
        feedback_rating_value = str(item.get("feedback_rating") or "").strip()
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
                due_date=(
                    date.fromisoformat(due_date_value) if due_date_value else None
                ),
                score=float(score_value) if score_value else None,
                feedback_rating=(
                    int(feedback_rating_value) if feedback_rating_value else None
                ),
            )
        )
        existing_record_ids.add(record_id)
    if additions:
        object.__setattr__(bundle, "history", (*bundle.history, *additions))
