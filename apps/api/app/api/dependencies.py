import os
import logging
from functools import lru_cache
from pathlib import Path

from app.application.journey_service import JourneyService
from app.infrastructure.dataset_loader import load_dataset, repository_dataset_dir
from app.infrastructure.llm_adapter import OpenAIRecommendationAdapter

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_journey_service() -> JourneyService:
    configured = os.getenv("DATASET_DIR")
    dataset_dir = Path(configured) if configured else repository_dataset_dir()
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
    return JourneyService(load_dataset(dataset_dir), reranker=reranker)
