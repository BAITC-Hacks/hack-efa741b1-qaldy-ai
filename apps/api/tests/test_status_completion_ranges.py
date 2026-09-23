import csv
import io
import shutil
from pathlib import Path

import pytest

from app.application.import_service import CSV_COLUMNS, ImportService
from app.infrastructure.dataset_loader import (
    DatasetError,
    load_dataset,
    repository_dataset_dir,
)
from app.infrastructure.sqlite_repository import SQLiteRepository


VALID_BOUNDARIES = (
    ("completed", 100),
    ("in_progress", 0),
    ("in_progress", 95),
    ("dropped", 5),
    ("dropped", 95),
    ("no_show", 0),
    ("declined", 0),
    ("overdue", 0),
    ("overdue", 95),
)

INVALID_BOUNDARIES = (
    ("completed", 99, "completed requires 100"),
    ("in_progress", 96, "in_progress requires a value in range 0..95"),
    ("dropped", 4, "dropped requires a value in range 5..95"),
    ("dropped", 96, "dropped requires a value in range 5..95"),
    ("no_show", 1, "no_show requires 0"),
    ("declined", 1, "declined requires 0"),
    ("overdue", 96, "overdue requires a value in range 0..95"),
)


def _copy_seed(tmp_path: Path) -> Path:
    target = tmp_path / "dataset"
    shutil.copytree(repository_dataset_dir(), target)
    return target


def _read_history(root: Path) -> tuple[list[str], list[dict[str, str]]]:
    with (root / "activity_history.csv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames is not None
        return reader.fieldnames, list(reader)


def _write_history(
    root: Path,
    fieldnames: list[str],
    rows: list[dict[str, str]],
) -> None:
    with (root / "activity_history.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _seed_row(status: str) -> dict[str, str]:
    _, rows = _read_history(repository_dataset_dir())
    return next(
        row
        for row in rows
        if row["status"] == status
        and (status != "completed" or row["event_id"] == "EV_036")
    )


def _csv_for_status(status: str, completion_pct: int) -> str:
    row = _seed_row(status)
    row.update(
        record_id=f"STATUS-RANGE-{status}-{completion_pct}",
        completion_pct=str(completion_pct),
    )
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerow(row)
    return output.getvalue()


def _empty_employee_document(bundle) -> dict[str, object]:
    return {
        "meta": {
            "dataset": "Career Quest",
            "version": bundle.dataset_version,
            "as_of_date": bundle.as_of_date.isoformat(),
        },
        "employees": [],
    }


def test_seed_loader_accepts_all_status_completion_boundaries(
    tmp_path: Path,
) -> None:
    root = _copy_seed(tmp_path)
    fieldnames, rows = _read_history(root)
    indexes_by_status = {
        status: [index for index, row in enumerate(rows) if row["status"] == status]
        for status, _ in VALID_BOUNDARIES
    }
    used_per_status: dict[str, int] = {}

    for status, completion_pct in VALID_BOUNDARIES:
        offset = used_per_status.get(status, 0)
        rows[indexes_by_status[status][offset]]["completion_pct"] = str(completion_pct)
        used_per_status[status] = offset + 1

    _write_history(root, fieldnames, rows)

    load_dataset(root)


@pytest.mark.parametrize(
    ("status", "completion_pct", "expected"),
    INVALID_BOUNDARIES,
)
def test_seed_loader_rejects_status_completion_outside_documented_range(
    tmp_path: Path,
    status: str,
    completion_pct: int,
    expected: str,
) -> None:
    root = _copy_seed(tmp_path)
    fieldnames, rows = _read_history(root)
    row = next(item for item in rows if item["status"] == status)
    row["completion_pct"] = str(completion_pct)
    _write_history(root, fieldnames, rows)

    with pytest.raises(DatasetError, match=expected):
        load_dataset(root)


@pytest.fixture
def import_service(tmp_path: Path) -> ImportService:
    bundle = load_dataset()
    return ImportService(bundle, SQLiteRepository(tmp_path / "career.db"))


@pytest.mark.parametrize(("status", "completion_pct"), VALID_BOUNDARIES)
def test_csv_import_accepts_all_status_completion_boundaries(
    import_service: ImportService,
    status: str,
    completion_pct: int,
) -> None:
    result = import_service.validate(
        _empty_employee_document(import_service.bundle),
        _csv_for_status(status, completion_pct),
    )

    assert result.valid is True, result.errors


@pytest.mark.parametrize(
    ("status", "completion_pct", "_expected"),
    INVALID_BOUNDARIES,
)
def test_csv_import_rejects_status_completion_outside_documented_range(
    import_service: ImportService,
    status: str,
    completion_pct: int,
    _expected: str,
) -> None:
    result = import_service.validate(
        _empty_employee_document(import_service.bundle),
        _csv_for_status(status, completion_pct),
    )

    assert any(
        issue.code == "status_mismatch"
        and issue.location == "row 2, completion_pct"
        for issue in result.errors
    )
