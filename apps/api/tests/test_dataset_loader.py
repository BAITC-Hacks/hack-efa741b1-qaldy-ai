import csv
import json
import shutil
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

import pytest

from app.infrastructure.dataset_loader import (
    DatasetError,
    load_dataset,
    repository_dataset_dir,
)


def _copy_seed(tmp_path: Path) -> Path:
    target = tmp_path / "dataset"
    shutil.copytree(repository_dataset_dir(), target)
    return target


def _mutate_json(
    root: Path,
    filename: str,
    mutation: Callable[[dict[str, Any]], None],
) -> None:
    path = root / filename
    document = json.loads(path.read_text(encoding="utf-8"))
    mutation(document)
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _mutate_first_history_row(
    root: Path,
    mutation: Callable[[dict[str, str]], None],
) -> None:
    path = root / "activity_history.csv"
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        rows = list(reader)
    assert fieldnames is not None
    mutation(rows[0])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_seed_dataset_contract() -> None:
    bundle = load_dataset()

    assert bundle.dataset_version == "1.0"
    assert bundle.as_of_date.isoformat() == "2026-10-01"
    assert len(bundle.skills) == 60
    assert len(bundle.role_profiles) == 32
    assert len(bundle.employees) == 200
    assert len(bundle.events) == 40
    assert len(bundle.history) == 2743
    assert bundle.events["EV_036"].repeatable is True
    assert all(
        event.repeatable is False
        for event_id, event in bundle.events.items()
        if event_id != "EV_036"
    )
    assert bundle.employees["E0001"].manager_id == "E0050"
    assert bundle.employees["E0001"].hire_date is not None
    assert bundle.employees["E0001"].tenure_months == 5
    assert bundle.history[0].score == 61
    assert bundle.history[0].feedback_rating == 5


def test_rejects_non_exact_activity_history_header(tmp_path: Path) -> None:
    root = _copy_seed(tmp_path)
    path = root / "activity_history.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    lines[0] += ",unexpected"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(DatasetError, match="expected exact header"):
        load_dataset(root)


@pytest.mark.parametrize(
    ("filename", "collection", "expected"),
    [
        ("skills.json", "skills", "duplicate skill_id"),
        ("employees.json", "employees", "duplicate employee_id"),
        ("events.json", "events", "duplicate event_id"),
    ],
)
def test_rejects_duplicate_json_ids_before_mapping_overwrite(
    tmp_path: Path,
    filename: str,
    collection: str,
    expected: str,
) -> None:
    root = _copy_seed(tmp_path)

    def duplicate_first(document: dict[str, Any]) -> None:
        document[collection].insert(1, deepcopy(document[collection][0]))

    _mutate_json(root, filename, duplicate_first)

    with pytest.raises(DatasetError, match=expected):
        load_dataset(root)


def test_rejects_duplicate_role_profile(tmp_path: Path) -> None:
    root = _copy_seed(tmp_path)

    def duplicate_profile(document: dict[str, Any]) -> None:
        document["role_profiles"].insert(
            1,
            deepcopy(document["role_profiles"][0]),
        )

    _mutate_json(root, "skills.json", duplicate_profile)

    with pytest.raises(DatasetError, match="duplicate role profile"):
        load_dataset(root)


def test_rejects_duplicate_history_record_id(tmp_path: Path) -> None:
    root = _copy_seed(tmp_path)
    path = root / "activity_history.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    lines.insert(2, lines[1])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    with pytest.raises(DatasetError, match="duplicate record_id"):
        load_dataset(root)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [("mandatory", "true"), ("repeatable", 1)],
)
def test_event_booleans_are_strict(
    tmp_path: Path,
    field: str,
    invalid_value: Any,
) -> None:
    root = _copy_seed(tmp_path)

    def corrupt_boolean(document: dict[str, Any]) -> None:
        document["events"][0][field] = invalid_value

    _mutate_json(root, "events.json", corrupt_boolean)

    with pytest.raises(DatasetError, match=rf"{field}: expected a boolean"):
        load_dataset(root)


@pytest.mark.parametrize(
    ("filename", "mutation", "expected"),
    [
        (
            "employees.json",
            lambda document: document["employees"][0].update(grade="Principal"),
            "unsupported grade",
        ),
        (
            "employees.json",
            lambda document: document["employees"][0]["skills"].update(
                SK_PYTHON=6
            ),
            "range 0..5",
        ),
        (
            "skills.json",
            lambda document: document["role_profiles"][0][
                "required_skills"
            ].update(SK_COMMUNICATION=-1),
            "range 0..5",
        ),
    ],
)
def test_rejects_invalid_grades_and_skill_levels(
    tmp_path: Path,
    filename: str,
    mutation: Callable[[dict[str, Any]], None],
    expected: str,
) -> None:
    root = _copy_seed(tmp_path)
    _mutate_json(root, filename, mutation)

    with pytest.raises(DatasetError, match=expected):
        load_dataset(root)


@pytest.mark.parametrize(
    ("filename", "mutation", "expected"),
    [
        (
            "employees.json",
            lambda document: document["employees"][0].update(role="Unknown Role"),
            "no role profile",
        ),
        (
            "employees.json",
            lambda document: document["employees"][0]["career_goal"].update(
                target_role="Unknown Role"
            ),
            "career_goal: no role profile",
        ),
        (
            "employees.json",
            lambda document: document["employees"][0]["skills"].update(
                SK_UNKNOWN=1
            ),
            "unknown skill_id 'SK_UNKNOWN'",
        ),
        (
            "events.json",
            lambda document: document["events"][0]["target_roles"].append(
                "Unknown Role"
            ),
            "target role/grade has no profile",
        ),
        (
            "events.json",
            lambda document: document["events"][3]["develops_skills"][0].update(
                skill_id="SK_UNKNOWN"
            ),
            "unknown skill_id 'SK_UNKNOWN'",
        ),
        (
            "events.json",
            lambda document: document["events"][0]["prerequisites"].update(
                SK_UNKNOWN=1
            ),
            "unknown skill_id 'SK_UNKNOWN'",
        ),
    ],
)
def test_rejects_broken_profile_and_skill_references(
    tmp_path: Path,
    filename: str,
    mutation: Callable[[dict[str, Any]], None],
    expected: str,
) -> None:
    root = _copy_seed(tmp_path)
    _mutate_json(root, filename, mutation)

    with pytest.raises(DatasetError, match=expected):
        load_dataset(root)


@pytest.mark.parametrize(
    ("field", "invalid_value", "expected"),
    [
        ("employee_id", "E9999", "unknown employee_id"),
        ("event_id", "EV_999", "unknown event_id"),
        ("status", "unknown", "unsupported status"),
        ("completion_pct", "101", "range 0..100"),
        ("score", "101", "range 0..100"),
        ("feedback_rating", "0", "range 1..5"),
        ("date", "2026-10-02", "after snapshot"),
    ],
)
def test_rejects_invalid_history_values_with_row_context(
    tmp_path: Path,
    field: str,
    invalid_value: str,
    expected: str,
) -> None:
    root = _copy_seed(tmp_path)
    _mutate_first_history_row(
        root,
        lambda row: row.update({field: invalid_value}),
    )

    with pytest.raises(DatasetError, match=rf"activity_history.csv row 2.*{expected}"):
        load_dataset(root)
