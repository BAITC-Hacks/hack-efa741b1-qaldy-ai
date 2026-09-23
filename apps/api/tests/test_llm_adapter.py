import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.application.journey_service import JourneyService
from app.infrastructure.dataset_loader import load_dataset
from app.infrastructure.llm_adapter import (
    AIRecommendationItem,
    AIRecommendationPlan,
    OpenAIRecommendationAdapter,
)


def journey_with_recommendations(*, within_score_band: bool = False):
    service = JourneyService(load_dataset())
    for employee_id in sorted(service.bundle.employees):
        journey = service.get_journey(employee_id)
        scores = [item.score for item in journey.recommendations]
        if not scores:
            continue
        if within_score_band and (len(scores) < 2 or max(scores) - min(scores) > 5):
            continue
        return journey
    raise AssertionError("Seed must contain matching recommendations")


class FakeResponses:
    def __init__(self, plan: AIRecommendationPlan):
        self.plan = plan
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_parsed=self.plan)


class FakeClock:
    def __init__(self) -> None:
        self.value = 100.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


def plan_for(journey, *, reverse: bool = False) -> AIRecommendationPlan:
    event_ids = [item.event_id for item in journey.recommendations]
    if reverse:
        event_ids.reverse()
    return AIRecommendationPlan(
        recommendations=[
            AIRecommendationItem(
                event_id=event_id,
                reason_codes=[
                    "career_goal",
                    "skill_gap",
                    "target_requirement",
                    "history",
                ],
            )
            for event_id in event_ids
        ]
    )


def test_ai_reranks_only_within_score_band_caches_and_omits_employee_id(
    caplog,
) -> None:
    journey = journey_with_recommendations(within_score_band=True)
    original_ids = [item.event_id for item in journey.recommendations]
    fake_responses = FakeResponses(plan_for(journey, reverse=True))
    adapter = OpenAIRecommendationAdapter(
        api_key="test",
        model="test-model",
        client=SimpleNamespace(responses=fake_responses),
    )

    with caplog.at_level(logging.INFO):
        first = adapter.rerank(journey)
        second = adapter.rerank(journey)

    assert [item.event_id for item in first] == list(reversed(original_ids))
    assert all(len(item.reasons) == 4 for item in first)
    assert all("Текущий грейд" in item.reasons[0] for item in first)
    assert all("требуется" in item.reasons[2] for item in first)
    assert second == first
    assert len(fake_responses.calls) == 1
    request = fake_responses.calls[0]
    payload = json.loads(request["input"][1]["content"])
    serialized_payload = json.dumps(payload, ensure_ascii=False)
    assert "employee_id" not in payload
    assert journey.employee.employee_id not in serialized_payload
    assert journey.employee.full_name not in serialized_payload
    assert journey.employee.employee_id not in caplog.text
    assert payload["target_requirements_and_gaps"]
    assert "history_status_counts" in payload
    assert request["max_output_tokens"] == 512


def test_structured_output_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        AIRecommendationItem.model_validate(
            {
                "event_id": "EV_001",
                "reason_codes": ["skill_gap", "invented_reason", "history"],
            }
        )

    schema = AIRecommendationPlan.model_json_schema()
    assert schema["additionalProperties"] is False
    assert schema["$defs"]["AIRecommendationItem"]["additionalProperties"] is False


def test_invented_event_id_falls_back_to_deterministic_result() -> None:
    journey = journey_with_recommendations()
    bad_plan = AIRecommendationPlan(
        recommendations=[
            AIRecommendationItem(
                event_id="EV_INVENTED",
                reason_codes=["career_goal", "skill_gap", "history"],
            )
        ]
    )
    adapter = OpenAIRecommendationAdapter(
        api_key="test",
        model="test-model",
        client=SimpleNamespace(responses=FakeResponses(bad_plan)),
    )
    service = JourneyService(load_dataset(), reranker=adapter)

    result = service.get_recommendations(journey.employee.employee_id)

    assert result.recommendation_mode == "deterministic"
    assert [item.event_id for item in result.recommendations] == [
        item.event_id for item in journey.recommendations
    ]
    assert "безопасный" in (result.recommendation_notice or "")


def test_duplicate_evidence_codes_fall_back_to_deterministic_result() -> None:
    journey = journey_with_recommendations()
    bad_plan = AIRecommendationPlan(
        recommendations=[
            AIRecommendationItem(
                event_id=item.event_id,
                reason_codes=["career_goal", "skill_gap", "skill_gap"],
            )
            for item in journey.recommendations
        ]
    )
    adapter = OpenAIRecommendationAdapter(
        api_key="test",
        model="test-model",
        client=SimpleNamespace(responses=FakeResponses(bad_plan)),
    )
    service = JourneyService(load_dataset(), reranker=adapter)

    result = service.get_recommendations(journey.employee.employee_id)

    assert result.recommendation_mode == "deterministic"
    assert result.recommendations == journey.recommendations


def test_materially_lower_score_cannot_be_promoted() -> None:
    journey = journey_with_recommendations()
    scores = [item.score for item in journey.recommendations]
    assert len(scores) >= 2 and max(scores) - min(scores) > 5
    fake_responses = FakeResponses(plan_for(journey, reverse=True))
    adapter = OpenAIRecommendationAdapter(
        api_key="test",
        model="test-model",
        client=SimpleNamespace(responses=fake_responses),
    )

    with pytest.raises(ValueError, match="score band"):
        adapter.rerank(journey)


def test_cache_is_lru_bounded_and_expires_by_monotonic_ttl() -> None:
    journey = journey_with_recommendations(within_score_band=True)
    other_evidence = replace(journey, target_role=f"{journey.target_role} II")
    clock = FakeClock()
    fake_responses = FakeResponses(plan_for(journey))
    adapter = OpenAIRecommendationAdapter(
        api_key="test",
        model="test-model",
        client=SimpleNamespace(responses=fake_responses),
        cache_ttl_seconds=10,
        cache_max_entries=1,
        clock=clock,
    )

    adapter.rerank(journey)
    adapter.rerank(other_evidence)
    assert len(fake_responses.calls) == 2
    assert len(adapter._cache) == 1

    adapter.rerank(journey)
    adapter.rerank(journey)
    assert len(fake_responses.calls) == 3

    clock.advance(11)
    adapter.rerank(journey)
    assert len(fake_responses.calls) == 4


def test_identical_concurrent_requests_use_single_flight() -> None:
    journey = journey_with_recommendations(within_score_band=True)

    class BlockingResponses(FakeResponses):
        def __init__(self, plan: AIRecommendationPlan) -> None:
            super().__init__(plan)
            self.started = threading.Event()
            self.release = threading.Event()

        def parse(self, **kwargs):
            self.calls.append(kwargs)
            self.started.set()
            assert self.release.wait(timeout=2)
            return SimpleNamespace(output_parsed=self.plan)

    fake_responses = BlockingResponses(plan_for(journey, reverse=True))
    adapter = OpenAIRecommendationAdapter(
        api_key="test",
        model="test-model",
        client=SimpleNamespace(responses=fake_responses),
        cache_max_entries=0,
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        leader = executor.submit(adapter.rerank, journey)
        assert fake_responses.started.wait(timeout=1)
        follower = executor.submit(adapter.rerank, journey)

        deadline = time.monotonic() + 1
        while time.monotonic() < deadline:
            with adapter._lock:
                if any(flight.waiters for flight in adapter._inflight.values()):
                    break
            time.sleep(0.001)
        else:
            pytest.fail("Second request did not join the in-flight request")

        fake_responses.release.set()
        assert follower.result(timeout=1) == leader.result(timeout=1)

    assert len(fake_responses.calls) == 1


def test_timeout_falls_back_without_breaking_user_flow() -> None:
    journey = journey_with_recommendations()

    class TimeoutReranker:
        def rerank(self, _journey):
            raise TimeoutError("provider timeout")

    service = JourneyService(load_dataset(), reranker=TimeoutReranker())
    result = service.get_recommendations(journey.employee.employee_id)

    assert result.recommendation_mode == "deterministic"
    assert result.recommendations
