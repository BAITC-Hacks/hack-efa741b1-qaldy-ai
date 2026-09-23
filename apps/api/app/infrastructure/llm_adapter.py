import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, replace
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict

from app.domain.models import EmployeeJourney, Recommendation

logger = logging.getLogger(__name__)
_PROMPT_VERSION = "recommendation-evidence-v4"
_MAX_SCORE_BAND = 5
ReasonCode = Literal["career_goal", "skill_gap", "target_requirement", "history"]
_REASON_CODES = frozenset({"career_goal", "skill_gap", "target_requirement", "history"})


class AIRecommendationItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    reason_codes: list[ReasonCode]


class AIRecommendationPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommendations: list[AIRecommendationItem]


@dataclass(frozen=True)
class _CacheEntry:
    expires_at: float
    plan: tuple[tuple[str, tuple[ReasonCode, ...]], ...]


@dataclass
class _InFlight:
    completed: threading.Event
    plan: tuple[tuple[str, tuple[ReasonCode, ...]], ...] | None = None
    error: BaseException | None = None
    waiters: int = 0


class OpenAIRecommendationAdapter:
    """Order eligible candidates and select explanations from verified evidence."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        timeout_seconds: float = 10.0,
        cache_ttl_seconds: float = 300.0,
        cache_max_entries: int = 512,
        max_output_tokens: int = 512,
        client: Any | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        if cache_ttl_seconds < 0:
            raise ValueError("cache_ttl_seconds must be non-negative")
        if cache_max_entries < 0:
            raise ValueError("cache_max_entries must be non-negative")
        if max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be positive")
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
        self._cache_ttl_seconds = cache_ttl_seconds
        self._cache_max_entries = cache_max_entries
        self._max_output_tokens = max_output_tokens
        self._clock = clock or time.monotonic
        self._cache: OrderedDict[str, _CacheEntry] = OrderedDict()
        self._inflight: dict[str, _InFlight] = {}
        self._lock = threading.Lock()

    def rerank(self, journey: EmployeeJourney) -> tuple[Recommendation, ...]:
        evidence = self._evidence(journey)
        cache_key = hashlib.sha256(
            json.dumps(
                {
                    "model": self._model,
                    "prompt_version": _PROMPT_VERSION,
                    "evidence": evidence,
                },
                ensure_ascii=False,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        now = self._clock()
        with self._lock:
            cached = self._get_cached(cache_key, now)
            if cached is not None:
                return self._recommendations_for(journey, cached)
            flight = self._inflight.get(cache_key)
            if flight is None:
                flight = _InFlight(completed=threading.Event())
                self._inflight[cache_key] = flight
                leader = True
            else:
                flight.waiters += 1
                leader = False

        if not leader:
            flight.completed.wait()
            if flight.error is not None:
                raise flight.error
            if flight.plan is None:
                raise RuntimeError("Rerank request completed without a result")
            return self._recommendations_for(journey, flight.plan)

        started = self._clock()
        try:
            response = self._client.responses.parse(
                model=self._model,
                input=[
                    {
                        "role": "system",
                        "content": (
                            "Ты карьерный AI-навигатор. Работай только с переданными "
                            "валидными кандидатами. Верни каждый event_id ровно один раз. "
                            "Для каждого кандидата верни все 4 разных reason_codes: "
                            "career_goal, skill_gap, target_requirement, history. "
                            "Коды задают порядок объяснения на основе проверенных данных; "
                            "не добавляй свободный текст, факты, навыки или мероприятия."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            evidence, ensure_ascii=False, sort_keys=True
                        ),
                    },
                ],
                text_format=AIRecommendationPlan,
                max_output_tokens=self._max_output_tokens,
                store=False,
            )
            plan = response.output_parsed
            if plan is None:
                raise ValueError("Model returned no structured output")

            selected = tuple(
                (item.event_id, tuple(item.reason_codes))
                for item in plan.recommendations
            )
            self._validate_plan(journey, selected)
        except BaseException as error:
            with self._lock:
                flight.error = error
                self._inflight.pop(cache_key, None)
                flight.completed.set()
            raise

        with self._lock:
            self._store_cached(cache_key, selected, self._clock())
            flight.plan = selected
            self._inflight.pop(cache_key, None)
            flight.completed.set()
        logger.info(
            "recommendation_ai_success evidence_hash=%s model=%s duration_ms=%d candidates=%d",
            cache_key[:12],
            self._model,
            round((self._clock() - started) * 1000),
            len(selected),
        )
        return self._recommendations_for(journey, selected)

    def _get_cached(
        self, cache_key: str, now: float
    ) -> tuple[tuple[str, tuple[ReasonCode, ...]], ...] | None:
        entry = self._cache.get(cache_key)
        if entry is None:
            return None
        if entry.expires_at <= now:
            del self._cache[cache_key]
            return None
        self._cache.move_to_end(cache_key)
        return entry.plan

    def _store_cached(
        self,
        cache_key: str,
        plan: tuple[tuple[str, tuple[ReasonCode, ...]], ...],
        now: float,
    ) -> None:
        if self._cache_ttl_seconds == 0 or self._cache_max_entries == 0:
            return
        expired = [
            key for key, entry in self._cache.items() if entry.expires_at <= now
        ]
        for key in expired:
            del self._cache[key]
        self._cache[cache_key] = _CacheEntry(
            expires_at=now + self._cache_ttl_seconds,
            plan=plan,
        )
        self._cache.move_to_end(cache_key)
        while len(self._cache) > self._cache_max_entries:
            self._cache.popitem(last=False)

    @staticmethod
    def _recommendations_for(
        journey: EmployeeJourney,
        plan: tuple[tuple[str, tuple[ReasonCode, ...]], ...],
    ) -> tuple[Recommendation, ...]:
        source = {item.event_id: item for item in journey.recommendations}
        return tuple(
            replace(
                source[event_id],
                reasons=tuple(
                    OpenAIRecommendationAdapter._reason(journey, source[event_id], code)
                    for code in reason_codes
                ),
            )
            for event_id, reason_codes in plan
        )

    @staticmethod
    def _validate_plan(
        journey: EmployeeJourney,
        plan: tuple[tuple[str, tuple[ReasonCode, ...]], ...],
    ) -> None:
        source = {item.event_id: item for item in journey.recommendations}
        event_ids = tuple(event_id for event_id, _ in plan)
        if len(event_ids) != len(set(event_ids)) or set(event_ids) != set(source):
            raise ValueError("Model changed the deterministic candidate set")

        for _, reason_codes in plan:
            if (
                len(reason_codes) != len(_REASON_CODES)
                or len(set(reason_codes)) != len(reason_codes)
                or set(reason_codes) != _REASON_CODES
            ):
                raise ValueError("Model returned unsupported or insufficient evidence codes")

        for earlier_index, earlier_id in enumerate(event_ids):
            earlier_score = source[earlier_id].score
            for later_id in event_ids[earlier_index + 1 :]:
                later_score = source[later_id].score
                if later_score - earlier_score > _MAX_SCORE_BAND:
                    raise ValueError(
                        "Model reordered candidates outside the allowed score band"
                    )

    @staticmethod
    def _reason(
        journey: EmployeeJourney, item: Recommendation, code: ReasonCode
    ) -> str:
        if code == "career_goal":
            alignment = next(
                factor.value for factor in item.factors if factor.code == "goal_alignment"
            )
            return (
                f"Текущий грейд {journey.employee.grade}; цель — "
                f"{journey.target_role} {journey.target_grade}. "
                f"Соответствие активности цели: {round(alignment * 100)}%."
            )
        if code == "skill_gap":
            return (
                f"Навык {item.skill}: уровень {item.current_level} → "
                f"{item.projected_level} после активности."
            )
        if code == "target_requirement":
            return (
                f"Для целевого уровня {journey.target_grade} по навыку "
                f"{item.skill} требуется {item.required_level}."
            )
        if code == "history":
            history = next(
                factor.value for factor in item.factors if factor.code == "history_fit"
            )
            return (
                f"{item.reasons[2]} Оценка фактора истории: "
                f"{round(history * 100)}%."
            )
        raise ValueError("Unsupported evidence code")

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
            "current_role": journey.employee.role,
            "current_grade": journey.employee.grade,
            "target_role": journey.target_role,
            "target_grade": journey.target_grade,
            "target_requirements_and_gaps": [
                {
                    "skill": gap.name,
                    "current_level": gap.current_level,
                    "required_level": gap.required_level,
                    "gap": gap.gap,
                    "critical": gap.critical,
                }
                for gap in journey.skill_gaps
            ],
            "history_status_counts": {
                status: sum(
                    record.status == status for record in journey.activity_history
                )
                for status in sorted({record.status for record in journey.activity_history})
            },
            "candidates": candidates,
        }
