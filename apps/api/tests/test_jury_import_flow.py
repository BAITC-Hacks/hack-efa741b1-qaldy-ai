import json

from fastapi.testclient import TestClient

from app.api.dependencies import get_import_service, get_journey_service
from app.application.import_service import ImportService
from app.application.journey_service import JourneyService
from app.infrastructure.dataset_loader import load_dataset
from app.infrastructure.sqlite_repository import SQLiteRepository
from app.main import create_app


def test_jury_profile_is_available_in_journey_and_hr_after_import(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DEMO_HR_TOKEN", "jury-test-hr-token-2026")
    monkeypatch.setenv(
        "DEMO_EMPLOYEE_TOKENS",
        json.dumps({"JURY-0001": "jury-test-employee-token-2026"}),
    )
    bundle = load_dataset()
    repository = SQLiteRepository(tmp_path / "jury.db")
    journey_service = JourneyService(bundle, completion_repository=repository)
    import_service = ImportService(bundle, repository)
    source = next(
        employee
        for employee in bundle.employees.values()
        if journey_service.get_journey(employee.employee_id).recommendations
    )
    goal = source.career_goal
    document = {
        "meta": {
            "dataset": "Career Quest",
            "version": bundle.dataset_version,
            "as_of_date": bundle.as_of_date.isoformat(),
        },
        "employees": [
            {
                "employee_id": "JURY-0001",
                "full_name": "Synthetic Jury Profile",
                "department": source.department,
                "role": source.role,
                "grade": source.grade,
                "work_format": source.work_format,
                "preferred_language": source.preferred_language,
                "career_goal": (
                    {"target_role": goal.target_role, "target_grade": goal.target_grade}
                    if goal
                    else None
                ),
                "skills": source.skills,
                "last_review_date": source.last_review_date.isoformat(),
                "manager_id": source.manager_id,
            }
        ],
    }

    app = create_app()
    app.dependency_overrides[get_import_service] = lambda: import_service
    app.dependency_overrides[get_journey_service] = lambda: journey_service
    client = TestClient(app)
    hr_headers = {"Authorization": "Bearer jury-test-hr-token-2026"}

    validation = client.post(
        "/api/v1/import/validate",
        json={"employees_json": document},
        headers=hr_headers,
    )
    assert validation.status_code == 200
    assert validation.json()["valid"] is True

    applied = client.post(
        "/api/v1/import/apply",
        json={
            "validation_token": validation.json()["validation_token"],
            "package_hash": validation.json()["package_hash"],
        },
        headers={**hr_headers, "Idempotency-Key": "jury-import-1"},
    )
    assert applied.status_code == 200
    assert applied.json()["inserted_employees"] == 1

    employees = client.get(
        "/api/v1/employees",
        params={"query": "JURY-0001"},
        headers=hr_headers,
    )
    assert employees.status_code == 200
    assert [item["employee_id"] for item in employees.json()] == ["JURY-0001"]

    recommendations = client.post(
        "/api/v1/employees/JURY-0001/recommendations",
        headers={"Authorization": "Bearer jury-test-employee-token-2026"},
    )
    assert recommendations.status_code == 200
    assert 1 <= len(recommendations.json()["recommendations"]) <= 3
    assert all(
        len(item["reasons"]) >= 3
        for item in recommendations.json()["recommendations"]
    )

    before_progress = recommendations.json()["progress"]["current_points"]
    participation_before = client.get(
        "/api/v1/hr/participation", headers=hr_headers
    ).json()["total_records"]
    event_id = recommendations.json()["recommendations"][0]["event_id"]
    completion = client.post(
        f"/api/v1/employees/JURY-0001/activities/{event_id}/complete",
        headers={
            "Authorization": "Bearer jury-test-employee-token-2026",
            "Idempotency-Key": "jury-completion-1",
        },
    )
    assert completion.status_code == 200
    assert completion.json()["journey"]["progress"]["current_points"] > before_progress
    participation_after = client.get(
        "/api/v1/hr/participation", headers=hr_headers
    ).json()["total_records"]
    assert participation_after == participation_before + 1

    hr = client.get("/api/v1/hr/skill-gaps", headers=hr_headers)
    assert hr.status_code == 200
    assert hr.json()["employee_count"] == len(bundle.employees)
