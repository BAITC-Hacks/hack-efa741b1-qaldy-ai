import copy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from app.application.import_service import ImportService, ValidationTokenError
from app.application.journey_service import JourneyService
from app.domain.errors import ActivityAlreadyCompleted
from app.infrastructure.dataset_loader import load_dataset
from app.infrastructure.sqlite_repository import SQLiteRepository

CSV_HEADER = (
    "record_id,employee_id,event_id,date,due_date,status,completion_pct,score,"
    "feedback_rating,assigned_by\n"
)


def employee_document(bundle, employee_id="E9001"):
    source = bundle.employees["E0001"]
    goal = None
    if source.career_goal:
        goal = {
            "target_role": source.career_goal.target_role,
            "target_grade": source.career_goal.target_grade,
        }
    employee = {
        "employee_id": employee_id,
        "full_name": "Import Test",
        "department": source.department,
        "role": source.role,
        "grade": source.grade,
        "manager_id": "E0050",
        "hire_date": "2026-01-01",
        "tenure_months": 8,
        "work_format": source.work_format,
        "preferred_language": source.preferred_language,
        "career_goal": goal,
        "skills": dict(source.skills),
        "last_review_date": "2026-09-01",
    }
    return {
        "meta": {
            "dataset": "Career Quest",
            "version": bundle.dataset_version,
            "as_of_date": bundle.as_of_date.isoformat(),
        },
        "employees": [employee],
    }


@pytest.fixture
def import_context(tmp_path):
    bundle = load_dataset()
    repository = SQLiteRepository(tmp_path / "career.db")
    return bundle, repository, ImportService(bundle, repository)


def test_16_import_rejects_unknown_ids_and_duplicate_ids_with_exact_locations(import_context):
    bundle, _, service = import_context
    document = employee_document(bundle)
    document["employees"][0]["skills"]["SK_UNKNOWN"] = 2
    document["employees"].append(copy.deepcopy(document["employees"][0]))
    csv_text = CSV_HEADER + "R9001,E_UNKNOWN,EV_UNKNOWN,2026-09-01,,completed,100,80,5,self\n"

    result = service.validate(document, csv_text)

    assert result.valid is False
    locations = {(error.code, error.file, error.location) for error in result.errors}
    assert ("unknown_skill_id", "employees.json", "$.employees[0].skills.SK_UNKNOWN") in locations
    assert ("duplicate_id", "employees.json", "$.employees[1].employee_id") in locations
    assert ("unknown_employee_id", "activity_history.csv", "row 2, employee_id") in locations
    assert ("unknown_event_id", "activity_history.csv", "row 2, event_id") in locations


def test_import_reports_invalid_nested_json_types_instead_of_raising(import_context):
    bundle, _, service = import_context
    document = employee_document(bundle)
    document["employees"][0].update(
        {
            "role": ["Backend Developer"],
            "grade": {"value": "Middle"},
            "manager_id": ["E0050"],
            "career_goal": {
                "target_role": ["Engineering Manager"],
                "target_grade": {"value": "Lead"},
            },
        }
    )

    result = service.validate(document)

    assert result.valid is False
    locations = {(error.code, error.location) for error in result.errors}
    assert ("invalid_type", "$.employees[0].role") in locations
    assert ("invalid_type", "$.employees[0].grade") in locations
    assert ("invalid_type", "$.employees[0].manager_id") in locations
    assert ("invalid_type", "$.employees[0].career_goal.target_role") in locations
    assert ("invalid_type", "$.employees[0].career_goal.target_grade") in locations


def test_import_rejects_invalid_employee_enums_and_manager_semantics(import_context):
    bundle, _, service = import_context
    document = employee_document(bundle)
    document["employees"][0]["work_format"] = "spaceship"
    document["employees"][0]["preferred_language"] = "de"
    document["employees"][0]["manager_id"] = "E0001"

    result = service.validate(document)

    assert result.valid is False
    locations = {(error.code, error.location) for error in result.errors}
    assert ("invalid_value", "$.employees[0].work_format") in locations
    assert ("invalid_value", "$.employees[0].preferred_language") in locations
    assert ("invalid_manager", "$.employees[0].manager_id") in locations


def test_import_rejects_extra_csv_headers_and_cells_without_hash_failure(import_context):
    bundle, _, service = import_context
    document = employee_document(bundle)
    extra_header = (
        CSV_HEADER.rstrip("\n")
        + ",unexpected\n"
        + "R9001,E9001,EV_036,2026-09-01,,completed,100,80,5,self,value\n"
    )
    extra_cell = (
        CSV_HEADER
        + "R9001,E9001,EV_036,2026-09-01,,completed,100,80,5,self,value\n"
    )

    header_result = service.validate(document, extra_header)
    cell_result = service.validate(document, extra_cell)

    assert header_result.valid is False
    assert cell_result.valid is False
    assert header_result.package_hash is None
    assert cell_result.package_hash is None
    assert any(error.code == "invalid_columns" for error in header_result.errors)
    assert any(error.code == "invalid_columns" for error in cell_result.errors)


def test_import_validates_optional_scores_ratings_and_status_progress(import_context):
    bundle, _, service = import_context
    rows = (
        "R9101,E9001,EV_036,2026-09-01,,completed,100,101,,self\n"
        "R9102,E9001,EV_036,2026-09-01,,completed,100,,6,self\n"
        "R9103,E9001,EV_036,2026-09-01,,in_progress,100,80.5,3,self\n"
        "R9104,E9001,EV_036,2026-09-01,,dropped,0,,,self\n"
    )

    result = service.validate(employee_document(bundle), CSV_HEADER + rows)

    assert result.valid is False
    locations = {(error.code, error.location) for error in result.errors}
    assert ("out_of_range", "row 2, score") in locations
    assert ("out_of_range", "row 3, feedback_rating") in locations
    assert ("status_mismatch", "row 4, completion_pct") in locations
    assert ("status_mismatch", "row 5, completion_pct") in locations


def test_import_accepts_empty_or_decimal_score_and_empty_or_bounded_rating(import_context):
    bundle, _, service = import_context
    rows = (
        "R9201,E9001,EV_036,2026-09-01,,completed,100,87.5,,self\n"
        "R9202,E9001,EV_036,2026-09-01,,completed,100,,5,self\n"
    )

    result = service.validate(employee_document(bundle), CSV_HEADER + rows)

    assert result.valid is True


def test_import_activation_preserves_employee_and_activity_profile_fields(import_context):
    bundle, _, service = import_context
    row = "R9250,E9001,EV_036,2026-09-01,2026-09-15,completed,100,80,5,hr\n"

    validation = service.validate(employee_document(bundle), CSV_HEADER + row)
    service.apply(
        validation.validation_token or "",
        validation.package_hash or "",
        "apply-profile-fields",
    )

    employee = bundle.employees["E9001"]
    record = next(item for item in bundle.history if item.record_id == "R9250")
    assert employee.manager_id == "E0050"
    assert employee.hire_date.isoformat() == "2026-01-01"
    assert employee.tenure_months == 8
    assert record.due_date.isoformat() == "2026-09-15"
    assert record.score == 80
    assert record.feedback_rating == 5


def test_import_rejects_second_non_repeatable_completion_from_seed(import_context):
    bundle, _, service = import_context
    existing = next(
        record
        for record in bundle.history
        if record.status == "completed" and not bundle.events[record.event_id].repeatable
    )
    document = employee_document(bundle)
    document["employees"] = []
    row = (
        f"R-SEED-CONFLICT,{existing.employee_id},{existing.event_id},"
        f"{existing.activity_date.isoformat()},,completed,100,,,self\n"
    )

    result = service.validate(document, CSV_HEADER + row)

    assert result.valid is False
    assert any(error.code == "non_repeatable_completion" for error in result.errors)


def test_import_allows_identical_persisted_non_repeatable_noop_but_rejects_new_record(
    import_context,
):
    bundle, _, service = import_context
    event_id = next(
        event_id for event_id, event in bundle.events.items() if not event.repeatable
    )
    row = f"R9301,E9001,{event_id},2026-09-01,,completed,100,80,5,self\n"
    first = service.validate(employee_document(bundle), CSV_HEADER + row)
    service.apply(first.validation_token or "", first.package_hash or "", "apply-r9301")

    identical = service.validate(employee_document(bundle), CSV_HEADER + row)
    conflicting = service.validate(
        employee_document(bundle),
        CSV_HEADER
        + f"R9302,E9001,{event_id},2026-09-01,,completed,100,80,5,self\n",
    )

    assert identical.valid is True
    assert conflicting.valid is False
    assert any(
        error.code == "non_repeatable_completion" for error in conflicting.errors
    )


def test_import_rejects_two_uploaded_completions_for_non_repeatable_event(import_context):
    bundle, _, service = import_context
    event_id = next(
        event_id for event_id, event in bundle.events.items() if not event.repeatable
    )
    rows = (
        f"R9401,E9001,{event_id},2026-09-01,,completed,100,,,self\n"
        f"R9402,E9001,{event_id},2026-09-02,,completed,100,,,self\n"
    )

    result = service.validate(employee_document(bundle), CSV_HEADER + rows)

    assert result.valid is False
    assert any(error.code == "non_repeatable_completion" for error in result.errors)


def test_18_reapplying_identical_package_is_idempotent_no_op(import_context):
    bundle, repository, service = import_context
    result = service.validate(employee_document(bundle))
    first = service.apply(result.validation_token or "", result.package_hash or "", "apply-1")
    second = service.apply(result.validation_token or "", result.package_hash or "", "apply-2")

    assert first.inserted_employees == 1
    assert second.batch_id == first.batch_id
    assert second.idempotent_replay is True
    assert len(repository.list_imported_employees()) == 1


def test_21_same_record_is_noop_but_changed_content_conflicts(import_context):
    bundle, repository, service = import_context
    document = employee_document(bundle)
    row = "R9001,E9001,EV_036,2026-09-01,,completed,100,80,5,self\n"
    valid = service.validate(document, CSV_HEADER + row)
    service.apply(valid.validation_token or "", valid.package_hash or "", "apply-1")

    identical = service.validate(document, CSV_HEADER + row)
    replay = service.apply(
        identical.validation_token or "", identical.package_hash or "", "apply-2"
    )
    assert replay.idempotent_replay is True

    changed = service.validate(
        {**document, "employees": []},
        CSV_HEADER + "R9001,E9001,EV_036,2026-09-02,,completed,100,80,5,self\n",
    )
    assert changed.valid is False
    assert any(error.code == "conflict" for error in changed.errors)
    assert len(repository.list_imported_history()) == 1


def test_22_invalid_row_keeps_working_tables_unchanged(import_context):
    bundle, repository, service = import_context
    invalid_csv = CSV_HEADER + "R9002,E9001,EV_036,2026-09-01,,completed,25,80,5,self\n"

    result = service.validate(employee_document(bundle), invalid_csv)

    assert result.valid is False
    assert any(error.code == "status_mismatch" for error in result.errors)
    assert repository.list_imported_employees() == []
    assert repository.list_imported_history() == []


def test_23_apply_rejects_changed_or_expired_token_and_replays_same_key(import_context):
    bundle, repository, _ = import_context
    start = datetime(2026, 9, 1, tzinfo=timezone.utc)
    service = ImportService(bundle, repository, token_ttl=timedelta(minutes=5))
    validation = service.validate(employee_document(bundle), now=start)

    with pytest.raises(ValidationTokenError, match="hash changed"):
        service.apply(validation.validation_token or "", "0" * 64, "k1", now=start)
    with pytest.raises(ValidationTokenError, match="expired"):
        service.apply(
            validation.validation_token or "",
            validation.package_hash or "",
            "k1",
            now=start + timedelta(minutes=6),
        )

    fresh = service.validate(employee_document(bundle), now=start)
    first = service.apply(fresh.validation_token or "", fresh.package_hash or "", "stable", now=start)
    replay = service.apply(fresh.validation_token or "", fresh.package_hash or "", "stable", now=start)
    assert replay.batch_id == first.batch_id
    assert replay.idempotent_replay is True


def test_26_parallel_completion_and_restart_do_not_double_apply(tmp_path):
    db_path = tmp_path / "career.db"
    repository = SQLiteRepository(db_path)
    activity_date = load_dataset().as_of_date

    def complete_once(_):
        local = SQLiteRepository(db_path)
        return local.record_completion("E0001", "EV_036", activity_date, "same-key")

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(complete_once, range(8)))

    assert sum(not replay for _, replay in results) == 1
    assert len({record.record_id for record, _ in results}) == 1
    restarted = SQLiteRepository(db_path)
    assert len(restarted.list_completion_records()) == 1


def test_27_mismatched_dataset_metadata_is_rejected(import_context):
    bundle, repository, service = import_context
    document = employee_document(bundle)
    document["meta"]["as_of_date"] = "2026-09-30"

    result = service.validate(document)

    assert result.valid is False
    assert any(
        error.code == "metadata_mismatch"
        and error.location == "$.meta.as_of_date"
        for error in result.errors
    )
    assert repository.list_imported_employees() == []


def test_completion_records_persist_across_repository_instances(tmp_path):
    db_path = tmp_path / "career.db"
    repository = SQLiteRepository(db_path)
    record, replay = repository.record_completion(
        "E0001", "EV_036", load_dataset().as_of_date, "persist-key"
    )

    reopened = SQLiteRepository(db_path)
    records = reopened.list_completion_records()

    assert replay is False
    assert records == (record,)


def test_repository_rejects_second_non_repeatable_completion_with_new_key(tmp_path):
    repository = SQLiteRepository(tmp_path / "completion-policy.db")
    activity_date = load_dataset().as_of_date
    repository.record_completion("E0001", "EV_001", activity_date, "first-key")

    with pytest.raises(ActivityAlreadyCompleted):
        repository.record_completion("E0001", "EV_001", activity_date, "second-key")


def test_completion_replay_restores_original_snapshot_after_restart(tmp_path):
    db_path = tmp_path / "snapshot.db"
    bundle = load_dataset()
    repository = SQLiteRepository(db_path)
    service = JourneyService(bundle, completion_repository=repository)
    employee_id = next(
        employee_id
        for employee_id in sorted(bundle.employees)
        if len(service.get_journey(employee_id).recommendations) >= 2
    )
    first_event = service.get_journey(employee_id).recommendations[0].event_id
    first = service.complete_activity(employee_id, first_event, "snapshot-first")

    second_event = service.get_journey(employee_id).recommendations[0].event_id
    service.complete_activity(employee_id, second_event, "snapshot-second")

    restarted = JourneyService(load_dataset(), completion_repository=SQLiteRepository(db_path))
    replay = restarted.complete_activity(employee_id, first_event, "snapshot-first")

    assert replay.idempotent_replay is True
    assert replay.record_id == first.record_id
    assert replay.changes == first.changes
    assert replay.journey == first.journey


def test_successful_import_advances_dataset_revision_once(import_context):
    bundle, repository, service = import_context
    before = repository.dataset_revision()
    validation = service.validate(employee_document(bundle))

    first = service.apply(
        validation.validation_token or "",
        validation.package_hash or "",
        "revision-first",
    )
    after_first = repository.dataset_revision()
    replay = service.apply(
        validation.validation_token or "",
        validation.package_hash or "",
        "revision-replay",
    )

    assert first.idempotent_replay is False
    assert after_first == before + 1
    assert replay.idempotent_replay is True
    assert repository.dataset_revision() == after_first
