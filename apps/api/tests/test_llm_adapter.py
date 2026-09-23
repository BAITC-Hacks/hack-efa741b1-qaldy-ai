import json
from types import SimpleNamespace

from app.application.journey_service import JourneyService
from app.infrastructure.dataset_loader import load_dataset
from app.infrastructure.llm_adapter import (
    AIRecommendationItem,
    AIRecommendationPlan,
    OpenAIRecommendationAdapter,
)


def journey_with_recommendations():
    service = JourneyService(load_dataset())
    for employee_id in sorted(service.bundle.employees):
        journey = service.get_journey(employee_id)
        if journey.recommendations:
            return journey
    raise AssertionError("Seed must contain recommendations")


class FakeResponses:
    def __init__(self, plan: AIRecommendationPlan):
        self.plan = plan
        self.calls = []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_parsed=self.plan)


def test_ai_reranks_only_valid_candidates_and_caches() -> None:
    journey = journey_with_recommendations()
    original_ids = [item.event_id for item in journey.recommendations]
    plan = AIRecommendationPlan(
        recommendations=[
            AIRecommendationItem(
                event_id=event_id,
                reasons=["Цель", "Разрыв", "Критичность"],
            )
            for event_id in reversed(original_ids)
        ]
    )
    fake_responses = FakeResponses(plan)
    fake_client = SimpleNamespace(responses=fake_responses)
    adapter = OpenAIRecommendationAdapter(
        api_key="test",
        model="test-model",
        client=fake_client,
    )

    first = adapter.rerank(journey)
    second = adapter.rerank(journey)

    assert [item.event_id for item in first] == list(reversed(original_ids))
    assert second == first
    assert len(fake_responses.calls) == 1
    payload = json.loads(fake_responses.calls[0]["input"][1]["content"])
    assert journey.employee.full_name not in json.dumps(payload, ensure_ascii=False)


def test_invented_event_id_falls_back_to_deterministic_result() -> None:
    journey = journey_with_recommendations()
    bad_plan = AIRecommendationPlan(
        recommendations=[
            AIRecommendationItem(
                event_id="EV_INVENTED",
                reasons=["Цель", "Разрыв", "История"],
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


def test_timeout_falls_back_without_breaking_user_flow() -> None:
    journey = journey_with_recommendations()

    class TimeoutReranker:
        def rerank(self, _journey):
            raise TimeoutError("provider timeout")

    service = JourneyService(load_dataset(), reranker=TimeoutReranker())
    result = service.get_recommendations(journey.employee.employee_id)

    assert result.recommendation_mode == "deterministic"
    assert result.recommendations
