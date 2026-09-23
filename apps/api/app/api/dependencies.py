import os
from functools import lru_cache
from pathlib import Path

from app.application.journey_service import JourneyService
from app.infrastructure.dataset_loader import load_dataset, repository_dataset_dir


@lru_cache(maxsize=1)
def get_journey_service() -> JourneyService:
    configured = os.getenv("DATASET_DIR")
    dataset_dir = Path(configured) if configured else repository_dataset_dir()
    return JourneyService(load_dataset(dataset_dir))
