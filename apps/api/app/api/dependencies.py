import os
import logging
from functools import lru_cache
from pathlib import Path

from app.application.import_service import ImportService, activate_imported_records
from app.application.journey_service import JourneyService
from app.domain.models import DatasetBundle
from app.infrastructure.dataset_loader import load_dataset, repository_dataset_dir
from app.infrastructure.llm_adapter import OpenAIRecommendationAdapter
from app.infrastructure.sqlite_repository import SQLiteRepository

logger = logging.getLogger(__name__)


def _database_path() -> Path:
    configured = os.getenv("DATABASE_URL", "").strip()
    if configured:
        prefix = "sqlite:///"
        if not configured.startswith(prefix):
            raise RuntimeError("Only sqlite:/// DATABASE_URL is supported by the MVP")
        return Path(configured[len(prefix) :]).resolve()
    return Path(__file__).resolve().parents[4] / "data" / "runtime" / "career_quest.db"


@lru_cache(maxsize=1)
def get_sqlite_repository() -> SQLiteRepository:
    return SQLiteRepository(_database_path())


@lru_cache(maxsize=1)
def get_dataset_bundle() -> DatasetBundle:
    configured = os.getenv("DATASET_DIR")
    dataset_dir = Path(configured) if configured else repository_dataset_dir()
    bundle = load_dataset(dataset_dir)
    repository = get_sqlite_repository()
    activate_imported_records(
        bundle,
        repository.list_imported_employees(),
        repository.list_imported_history(),
    )
    return bundle


@lru_cache(maxsize=1)
def get_journey_service() -> JourneyService:
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
        get_dataset_bundle(),
        reranker=reranker,
        completion_repository=get_sqlite_repository(),
    )


@lru_cache(maxsize=1)
def get_import_service() -> ImportService:
    return ImportService(get_dataset_bundle(), get_sqlite_repository())
