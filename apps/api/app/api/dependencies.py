import os
import logging
from functools import lru_cache
from pathlib import Path

from app.application.import_service import ImportService, activate_imported_records
from app.application.journey_service import JourneyService
from app.api.auth import assert_auth_configuration
from app.domain.models import DatasetBundle
from app.infrastructure.dataset_loader import load_dataset, repository_dataset_dir
from app.infrastructure.llm_adapter import OpenAIRecommendationAdapter
from app.infrastructure.sqlite_repository import SQLiteRepository

logger = logging.getLogger(__name__)

_NON_LOCAL_ENVIRONMENTS = {"cloud", "production", "prod", "staging"}


def _database_path() -> Path:
    configured = os.getenv("DATABASE_URL", "").strip()
    if configured:
        prefix = "sqlite:///"
        if not configured.startswith(prefix):
            raise RuntimeError("Only sqlite:/// DATABASE_URL is supported by the MVP")
        return Path(configured[len(prefix) :]).resolve()
    app_env = os.getenv("APP_ENV", "development").strip().lower()
    if app_env in _NON_LOCAL_ENVIRONMENTS or os.getenv("VERCEL"):
        raise RuntimeError(
            "DATABASE_URL must be set explicitly in public/cloud environments; "
            "the repository-local SQLite database is a development default"
        )
    dataset_dir = repository_dataset_dir()
    repository_root = dataset_dir.parents[2]
    return repository_root / "data" / "runtime" / "career_quest.db"


@lru_cache(maxsize=1)
def get_sqlite_repository() -> SQLiteRepository:
    return SQLiteRepository(_database_path())


@lru_cache(maxsize=8)
def _get_dataset_bundle_for_revision(
    revision: int,
    dataset_dir_value: str,
) -> DatasetBundle:
    del revision  # The revision is intentionally part of the cache key.
    dataset_dir = Path(dataset_dir_value)
    bundle = load_dataset(dataset_dir)
    repository = get_sqlite_repository()
    activate_imported_records(
        bundle,
        repository.list_imported_employees(),
        repository.list_imported_history(),
    )
    return bundle


def get_dataset_bundle() -> DatasetBundle:
    configured = os.getenv("DATASET_DIR")
    dataset_dir = Path(configured) if configured else repository_dataset_dir()
    revision = get_sqlite_repository().dataset_revision()
    return _get_dataset_bundle_for_revision(revision, str(dataset_dir.resolve()))


def assert_backend_ready() -> None:
    """Validate both required runtime dependencies or raise with a clear cause."""
    assert_auth_configuration()
    bundle = get_dataset_bundle()
    missing_collections = [
        name
        for name, values in (
            ("employees", bundle.employees),
            ("skills", bundle.skills),
            ("role_profiles", bundle.role_profiles),
            ("events", bundle.events),
        )
        if not values
    ]
    if missing_collections:
        raise RuntimeError(
            "Dataset is loaded but required collections are empty: "
            + ", ".join(missing_collections)
        )
    get_sqlite_repository().ping()


@lru_cache(maxsize=8)
def _get_journey_service_for_revision(
    revision: int,
    dataset_dir_value: str,
) -> JourneyService:
    reranker = None
    enabled = os.getenv("LLM_ENABLED", "false").strip().lower() in {"1", "true", "yes"}
    api_key = os.getenv("LLM_API_KEY", "").strip()
    if enabled and api_key:
        timeout = min(10.0, max(0.1, float(os.getenv("LLM_TIMEOUT_SECONDS", "10"))))
        reranker = OpenAIRecommendationAdapter(
            api_key=api_key,
            model=os.getenv("LLM_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini",
            base_url=os.getenv("LLM_BASE_URL", "").strip() or None,
            timeout_seconds=timeout,
        )
    elif enabled:
        logger.warning("LLM_ENABLED is true but LLM_API_KEY is empty; fallback is active")
    return JourneyService(
        _get_dataset_bundle_for_revision(revision, dataset_dir_value),
        reranker=reranker,
        completion_repository=get_sqlite_repository(),
    )


def get_journey_service() -> JourneyService:
    revision = get_sqlite_repository().dataset_revision()
    configured = os.getenv("DATASET_DIR")
    dataset_dir = Path(configured) if configured else repository_dataset_dir()
    return _get_journey_service_for_revision(revision, str(dataset_dir.resolve()))


@lru_cache(maxsize=8)
def _get_import_service_for_revision(
    revision: int,
    dataset_dir_value: str,
) -> ImportService:
    return ImportService(
        _get_dataset_bundle_for_revision(revision, dataset_dir_value),
        get_sqlite_repository(),
    )


def get_import_service() -> ImportService:
    revision = get_sqlite_repository().dataset_revision()
    configured = os.getenv("DATASET_DIR")
    dataset_dir = Path(configured) if configured else repository_dataset_dir()
    return _get_import_service_for_revision(revision, str(dataset_dir.resolve()))


def clear_runtime_caches() -> None:
    """Clear process-local dependency caches after configuration changes/tests."""
    _get_import_service_for_revision.cache_clear()
    _get_journey_service_for_revision.cache_clear()
    _get_dataset_bundle_for_revision.cache_clear()
    get_sqlite_repository.cache_clear()
