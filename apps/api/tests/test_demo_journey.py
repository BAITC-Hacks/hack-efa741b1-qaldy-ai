from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_demo_journey_has_explainable_recommendations() -> None:
    response = client.get("/api/v1/demo/employee-journey")

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "demo"
    assert body["employee"]["target_grade"] == "Senior"
    assert 1 <= len(body["recommendations"]) <= 3
    assert all(len(item["reasons"]) >= 3 for item in body["recommendations"])
