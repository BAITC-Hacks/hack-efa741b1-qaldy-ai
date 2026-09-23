from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import dependencies
from app.api.routes import health
from app.infrastructure.sqlite_repository import SQLiteRepository
from app.main import app, create_app

client = TestClient(app)


def test_health_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEMO_HR_TOKEN", "test-health-token-123456")
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "career-quest-api",
        "version": "0.1.0",
    }


def test_livez_does_not_run_readiness_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_if_called() -> None:
        raise AssertionError("liveness must not touch dataset or database")

    monkeypatch.setattr(health, "assert_backend_ready", fail_if_called)

    response = client.get("/livez")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.parametrize("path", ["/health", "/readyz"])
def test_readiness_endpoints_return_503_when_dependency_fails(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    def fail() -> None:
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(health, "assert_backend_ready", fail)

    response = client.get(path)

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Required dataset or database is unavailable"
    }


def test_sqlite_ping_executes_readiness_query(tmp_path: Path) -> None:
    repository = SQLiteRepository(tmp_path / "readiness.db")

    repository.ping()


def test_production_requires_explicit_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL must be set explicitly"):
        dependencies._database_path()


def test_development_keeps_repository_sqlite_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert dependencies._database_path().name == "career_quest.db"


def test_vercel_requires_explicit_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(RuntimeError, match="DATABASE_URL must be set explicitly"):
        dependencies._database_path()


def test_lifespan_fails_fast_when_backend_is_not_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import app.main as main_module

    def fail() -> None:
        raise RuntimeError("dataset unavailable")

    monkeypatch.setattr(main_module, "assert_backend_ready", fail)

    with pytest.raises(RuntimeError, match="dataset unavailable"):
        with TestClient(create_app()):
            pass
