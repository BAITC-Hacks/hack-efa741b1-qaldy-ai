import hashlib
import json
import logging
import threading
import time
from typing import Any

from pydantic import BaseModel

from app.domain.models import EmployeeJourney, Recommendation

logger = logging.getLogger(__name__)


class AIRecommendationItem(BaseModel):
    event_id: str


class AIRecommendationPlan(BaseModel):
    recommendations: list[AIRecommendationItem]


class OpenAIRecommendationAdapter:
    """Rerank deterministic candidates without expanding the eligible set."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        timeout_seconds: float = 10.0,
        client: Any | None = None,
    ) -> None:
        if client is None:
            from openai import OpenAI

            client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=timeout_seconds,
                max_retries=0,
            )
        self._client = client
        self._model = model
        self._cache: dict[str, tuple[Recommendation, ...]] = {}
        self._lock = threading.Lock()

    def rerank(self, journey: EmployeeJourney) -> tuple[Recommendation, ...]:
        evidence = self._evidence(journey)
        cache_key = hashlib.sha256(
            json.dumps(evidence, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        with self._lock:
            cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        started = time.monotonic()
        response = self._client.responses.parse(
            model=self._model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Ты карьерный AI-навигатор. Работай только с переданными "
                        "валидными кандидатами. Верни каждый event_id ровно один раз "
                        "и измени только порядок. Не добавляй объяснения или другие поля."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(evidence, ensure_ascii=False, sort_keys=True),
                },
            ],
            text_format=AIRecommendationPlan,
            store=False,
        )
        plan = response.output_parsed
        if plan is None:
            raise ValueError("Model returned no structured output")

        source = {item.event_id: item for item in journey.recommendations}
        returned_ids = [item.event_id for item in plan.recommendations]
        if len(returned_ids) != len(set(returned_ids)) or set(returned_ids) != set(source):
            raise ValueError("Model changed the deterministic candidate set")

        reranked: list[Recommendation] = []
        for item in plan.recommendations:
            reranked.append(source[item.event_id])

        result = tuple(reranked)
        with self._lock:
            self._cache[cache_key] = result
        logger.info(
            "recommendation_ai_success employee_id=%s model=%s duration_ms=%d candidates=%d",
            journey.employee.employee_id,
            self._model,
            round((time.monotonic() - started) * 1000),
            len(result),
        )
        return result

    def _evidence(self, journey: EmployeeJourney) -> dict[str, Any]:
        candidates = []
        for item in journey.recommendations:
            candidates.append(
                {
                    "event_id": item.event_id,
                    "title": item.title,
                    "deterministic_score": item.score,
                    "kind": item.kind,
                    "format": item.event_format,
                    "duration_hours": item.duration_hours,
                    "skill": item.skill,
                    "current_level": item.current_level,
                    "projected_level": item.projected_level,
                    "required_level": item.required_level,
                    "factors": {
                        factor.code: factor.value for factor in item.factors
                    },
                }
            )
        return {
            "dataset_version": journey.dataset_version,
            "as_of_date": journey.as_of_date.isoformat(),
            "employee_id": journey.employee.employee_id,
            "current_grade": journey.employee.grade,
            "target_role": journey.target_role,
            "target_grade": journey.target_grade,
            "candidates": candidates,
        }
