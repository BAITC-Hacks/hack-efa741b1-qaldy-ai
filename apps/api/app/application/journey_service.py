import math
import logging
import threading
import uuid
from collections import Counter
from dataclasses import replace
from datetime import date
from typing import Any, Protocol

from pydantic import TypeAdapter

from app.domain.models import (
    ActivityRecord,
    ActivitySummary,
    CompletionResult,
    Continuation,
    CurrentSkill,
    DatasetBundle,
    DevelopmentEvent,
    Employee,
    EmployeeJourney,
    FactorScore,
    Grade,
    ProgressMetric,
    Recommendation,
    RoleProfile,
    SkillChange,
    SkillGap,
)
from app.domain.errors import ActivityAlreadyCompleted

GRADE_ORDER: tuple[Grade, ...] = ("Junior", "Middle", "Senior", "Lead")
WEIGHTS = {
    "gap_coverage": 0.40,
    "critical_coverage": 0.20,
    "goal_alignment": 0.15,
    "history_fit": 0.15,
    "availability": 0.05,
    "effort_fit": 0.05,
}
REASON_PRIORITY = (
    "no_target",
    "catalog_gap",
    "prerequisite_blocked",
    "already_in_progress",
    "already_completed",
    "no_future_session",
    "no_gap",
    "audience_mismatch",
)
logger = logging.getLogger(__name__)
COMPLETION_RESULT_ADAPTER = TypeAdapter(CompletionResult)


class RecommendationReranker(Protocol):
    def rerank(self, journey: EmployeeJourney) -> tuple[Recommendation, ...]: ...


class CompletionRepository(Protocol):
    def list_completion_records(self) -> tuple[ActivityRecord, ...]: ...

    def find_completion(
        self, employee_id: str, event_id: str, idempotency_key: str
    ) -> ActivityRecord | None: ...

    def record_completion(
        self,
        employee_id: str,
        event_id: str,
        activity_date: date,
        idempotency_key: str,
        repeatable: bool = False,
    ) -> tuple[ActivityRecord, bool]: ...

    def find_completion_snapshot(
        self, employee_id: str, event_id: str, idempotency_key: str
    ) -> dict[str, Any] | None: ...

    def save_completion_snapshot(
        self,
        employee_id: str,
        event_id: str,
        idempotency_key: str,
        snapshot: dict[str, Any],
    ) -> None: ...


class JourneyError(RuntimeError):
    pass


class EmployeeNotFound(JourneyError):
    pass


class EventNotFound(JourneyError):
    pass


class CompletionConflict(JourneyError):
    pass


class JourneyService:
    def __init__(
        self,
        bundle: DatasetBundle,
        reranker: RecommendationReranker | None = None,
        completion_repository: CompletionRepository | None = None,
    ):
        self.bundle = bundle
        self._reranker = reranker
        self._completion_repository = completion_repository
        self._overlay: list[ActivityRecord] = []
        self._idempotency: dict[tuple[str, str, str], CompletionResult] = {}
        self._lock = threading.RLock()

    def list_employees(self, query: str | None = None, limit: int = 50) -> list[Employee]:
        employees = sorted(self.bundle.employees.values(), key=lambda item: item.employee_id)
        if query:
            needle = query.casefold()
            employees = [
                item
                for item in employees
                if needle in item.employee_id.casefold()
                or needle in item.full_name.casefold()
                or needle in item.role.casefold()
            ]
        return employees[:limit]

    def get_journey(self, employee_id: str) -> EmployeeJourney:
        employee = self.bundle.employees.get(employee_id)
        if employee is None:
            raise EmployeeNotFound(employee_id)

        target_profile, target_reason = self._target_profile(employee)
        records = self._employee_records(employee_id)
        effective = self._effective_skills(employee, records)
        gaps = self._skill_gaps(target_profile, effective)
        progress = self._progress(target_profile, effective)
        latest = self._latest_by_event(records)
        continuations = tuple(
            Continuation(
                event_id=event_id,
                title=self.bundle.events[event_id].title,
                completion_pct=record.completion_pct,
            )
            for event_id, record in sorted(latest.items())
            if record.status == "in_progress" and event_id in self.bundle.events
        )

        recommendations, reason_counts = self._recommendations(
            employee=employee,
            target_profile=target_profile,
            effective=effective,
            gaps=gaps,
            records=records,
            latest=latest,
        )
        if target_reason == "no_target":
            reason_counts["no_target"] += 1
        primary_reason = None
        if not recommendations:
            primary_reason = next(
                (reason for reason in REASON_PRIORITY if reason_counts.get(reason, 0)),
                "catalog_gap",
            )

        return EmployeeJourney(
            source="dataset",
            dataset_version=self.bundle.dataset_version,
            as_of_date=self.bundle.as_of_date,
            employee=employee,
            target_role=target_profile.role,
            target_grade=target_profile.grade,
            target_reason=target_reason,
            progress=progress,
            current_skills=tuple(
                CurrentSkill(
                    skill_id=skill_id,
                    name=self.bundle.skills[skill_id].name,
                    level=level,
                )
                for skill_id, level in sorted(effective.items())
                if skill_id in self.bundle.skills
            ),
            skill_gaps=tuple(gaps),
            recommendations=tuple(recommendations),
            continuations=continuations,
            activity_history=tuple(
                ActivitySummary(
                    record_id=record.record_id,
                    event_id=record.event_id,
                    title=self.bundle.events[record.event_id].title,
                    activity_date=record.activity_date,
                    due_date=record.due_date,
                    status=record.status,
                    completion_pct=record.completion_pct,
                    score=record.score,
                    feedback_rating=record.feedback_rating,
                    assigned_by=record.assigned_by,
                    source=record.source,
                )
                for record in reversed(records)
                if record.event_id in self.bundle.events
            ),
            primary_reason=primary_reason,
            reason_counts=dict(reason_counts),
        )

    def get_recommendations(self, employee_id: str) -> EmployeeJourney:
        journey = self.get_journey(employee_id)
        if not journey.recommendations:
            return journey
        if self._reranker is None:
            return replace(
                journey,
                recommendation_notice=(
                    "AI отключён: показан проверяемый детерминированный рейтинг."
                ),
            )
        try:
            recommendations = self._reranker.rerank(journey)
        except Exception as error:  # LLM is never a single point of failure.
            logger.warning(
                "recommendation_fallback error_type=%s",
                type(error).__name__,
            )
            return replace(
                journey,
                recommendation_notice=(
                    "AI временно недоступен: показан безопасный детерминированный рейтинг."
                ),
            )
        return replace(
            journey,
            recommendations=recommendations,
            recommendation_mode="ai",
            recommendation_notice=(
                "AI уточнил порядок среди валидных кандидатов и выбрал факторы "
                "объяснения; формулировки составлены из проверенных данных."
            ),
        )

    def complete_activity(
        self,
        employee_id: str,
        event_id: str,
        idempotency_key: str,
    ) -> CompletionResult:
        if not idempotency_key.strip():
            raise CompletionConflict("Idempotency-Key is required")
        employee = self.bundle.employees.get(employee_id)
        if employee is None:
            raise EmployeeNotFound(employee_id)
        event = self.bundle.events.get(event_id)
        if event is None:
            raise EventNotFound(event_id)

        key = (employee_id, event_id, idempotency_key)
        with self._lock:
            if self._completion_repository is None:
                previous = self._idempotency.get(key)
                if previous is not None:
                    return replace(previous, idempotent_replay=True)
            else:
                persisted = self._completion_repository.find_completion(
                    employee_id, event_id, idempotency_key
                )
                if persisted is not None:
                    snapshot = self._completion_repository.find_completion_snapshot(
                        employee_id, event_id, idempotency_key
                    )
                    if snapshot is not None:
                        previous = COMPLETION_RESULT_ADAPTER.validate_python(snapshot)
                        return replace(previous, idempotent_replay=True)
                    result = self._build_completion_result(
                        employee, event, persisted, idempotent_replay=True
                    )
                    self._save_completion_snapshot(key, result)
                    return result

            before_journey = self.get_journey(employee_id)
            if event_id not in {item.event_id for item in before_journey.recommendations}:
                raise CompletionConflict("Activity is not an active recommendation")

            existing_completed = any(
                record.event_id == event_id and record.status == "completed"
                for record in self._employee_records(employee_id)
            )
            if existing_completed and not event.repeatable:
                raise CompletionConflict("Activity has already been completed")

            if self._completion_repository is None:
                record = ActivityRecord(
                    record_id=f"OVL-{uuid.uuid4()}",
                    employee_id=employee_id,
                    event_id=event_id,
                    activity_date=self.bundle.as_of_date,
                    status="completed",
                    completion_pct=100,
                    assigned_by="self",
                    source="overlay",
                )
                self._overlay.append(record)
                replay = False
            else:
                try:
                    record, replay = self._completion_repository.record_completion(
                        employee_id,
                        event_id,
                        self.bundle.as_of_date,
                        idempotency_key,
                        repeatable=event.repeatable,
                    )
                except ActivityAlreadyCompleted as error:
                    raise CompletionConflict("Activity has already been completed") from error
            result = self._build_completion_result(
                employee, event, record, idempotent_replay=replay
            )
            if self._completion_repository is None:
                self._idempotency[key] = result
            else:
                if replay:
                    snapshot = self._completion_repository.find_completion_snapshot(
                        employee_id, event_id, idempotency_key
                    )
                    if snapshot is not None:
                        previous = COMPLETION_RESULT_ADAPTER.validate_python(snapshot)
                        return replace(previous, idempotent_replay=True)
                self._save_completion_snapshot(key, result)
            return result

    def _save_completion_snapshot(
        self,
        key: tuple[str, str, str],
        result: CompletionResult,
    ) -> None:
        if self._completion_repository is None:
            return
        snapshot = COMPLETION_RESULT_ADAPTER.dump_python(result, mode="json")
        self._completion_repository.save_completion_snapshot(*key, snapshot)

    def _build_completion_result(
        self,
        employee: Employee,
        event: DevelopmentEvent,
        record: ActivityRecord,
        idempotent_replay: bool,
    ) -> CompletionResult:
        after_records = self._employee_records(employee.employee_id)
        before_records = [item for item in after_records if item.record_id != record.record_id]
        before_skills = self._effective_skills(employee, before_records)
        after_skills = self._effective_skills(employee, after_records)
        changes = tuple(
            SkillChange(
                skill_id=gain.skill_id,
                name=self.bundle.skills[gain.skill_id].name,
                before=before_skills.get(gain.skill_id, 0),
                after=after_skills.get(gain.skill_id, 0),
                applied_gain=after_skills.get(gain.skill_id, 0)
                - before_skills.get(gain.skill_id, 0),
            )
            for gain in event.develops_skills
        )
        return CompletionResult(
            record_id=record.record_id,
            idempotent_replay=idempotent_replay,
            changes=changes,
            journey=self.get_journey(employee.employee_id),
        )

    def _target_profile(self, employee: Employee) -> tuple[RoleProfile, str]:
        if employee.career_goal:
            key = (
                employee.career_goal.target_role,
                employee.career_goal.target_grade,
            )
            reason = "career_goal"
        else:
            index = GRADE_ORDER.index(employee.grade)
            if index < len(GRADE_ORDER) - 1:
                key = (employee.role, GRADE_ORDER[index + 1])
                reason = "next_grade"
            else:
                key = (employee.role, employee.grade)
                reason = "no_target"
        try:
            return self.bundle.role_profiles[key], reason
        except KeyError as error:
            raise JourneyError(f"Missing role profile: {key}") from error

    def _employee_records(self, employee_id: str) -> list[ActivityRecord]:
        seen: set[str] = set()
        records: list[ActivityRecord] = []
        persisted = (
            self._completion_repository.list_completion_records()
            if self._completion_repository is not None
            else ()
        )
        for record in (*self.bundle.history, *self._overlay, *persisted):
            if record.employee_id != employee_id or record.record_id in seen:
                continue
            seen.add(record.record_id)
            records.append(record)
        return sorted(records, key=lambda item: (item.activity_date, item.record_id))

    def _effective_skills(
        self, employee: Employee, records: list[ActivityRecord]
    ) -> dict[str, int]:
        levels = dict(employee.skills)
        for record in records:
            if record.status != "completed" or record.activity_date <= employee.last_review_date:
                continue
            event = self.bundle.events.get(record.event_id)
            if event is None:
                continue
            for gain in event.develops_skills:
                current = levels.get(gain.skill_id, 0)
                levels[gain.skill_id] = min(
                    5, max(current, min(current + gain.gain, gain.max_level))
                )
        return levels

    def _skill_gaps(
        self, profile: RoleProfile, effective: dict[str, int]
    ) -> list[SkillGap]:
        gaps = []
        for skill_id, required in profile.required_skills.items():
            current = effective.get(skill_id, 0)
            gap = max(0, required - current)
            if not gap:
                continue
            gaps.append(
                SkillGap(
                    skill_id=skill_id,
                    name=self.bundle.skills[skill_id].name,
                    current_level=current,
                    required_level=required,
                    gap=gap,
                    critical=skill_id in profile.critical_skills,
                )
            )
        return sorted(gaps, key=lambda item: (-int(item.critical), -item.gap, item.skill_id))

    @staticmethod
    def _progress(profile: RoleProfile, effective: dict[str, int]) -> ProgressMetric:
        required_points = sum(profile.required_skills.values())
        current_points = sum(
            min(effective.get(skill_id, 0), required)
            for skill_id, required in profile.required_skills.items()
        )
        percentage = 100 if not required_points else round(current_points / required_points * 100)
        return ProgressMetric(
            current_points=current_points,
            required_points=required_points,
            percentage=percentage,
        )

    @staticmethod
    def _latest_by_event(records: list[ActivityRecord]) -> dict[str, ActivityRecord]:
        latest: dict[str, ActivityRecord] = {}
        for record in records:
            latest[record.event_id] = record
        return latest

    def _recommendations(
        self,
        employee: Employee,
        target_profile: RoleProfile,
        effective: dict[str, int],
        gaps: list[SkillGap],
        records: list[ActivityRecord],
        latest: dict[str, ActivityRecord],
    ) -> tuple[list[Recommendation], Counter[str]]:
        gap_map = {item.skill_id: item for item in gaps}
        weighted_gap_total = sum(item.gap * (2 if item.critical else 1) for item in gaps)
        critical_gap_total = sum(item.gap for item in gaps if item.critical)
        completed = {
            record.event_id for record in records if record.status == "completed"
        }
        reasons: Counter[str] = Counter()
        candidates: list[Recommendation] = []

        for event in self.bundle.events.values():
            if event.mandatory:
                continue
            kind = self._candidate_kind(employee, target_profile, event)
            if kind is None:
                reasons["audience_mismatch"] += 1
                continue
            if event.event_id in completed and not event.repeatable:
                reasons["already_completed"] += 1
                continue
            if latest.get(event.event_id) and latest[event.event_id].status == "in_progress":
                reasons["already_in_progress"] += 1
                continue
            if event.event_format != "self_paced" and not any(
                session >= self.bundle.as_of_date for session in event.upcoming_sessions
            ):
                reasons["no_future_session"] += 1
                continue
            if any(
                effective.get(skill_id, 0) < required
                for skill_id, required in event.prerequisites.items()
            ):
                reasons["prerequisite_blocked"] += 1
                continue

            impacts: dict[str, int] = {}
            for gain in event.develops_skills:
                gap = gap_map.get(gain.skill_id)
                if gap is None:
                    continue
                actual_gain = min(
                    gap.gap,
                    max(
                        0,
                        min(effective.get(gain.skill_id, 0) + gain.gain, gain.max_level)
                        - effective.get(gain.skill_id, 0),
                    ),
                )
                if actual_gain:
                    impacts[gain.skill_id] = actual_gain
            if not impacts:
                reasons["no_gap"] += 1
                continue

            candidate = self._score_candidate(
                employee=employee,
                event=event,
                kind=kind,
                impacts=impacts,
                gap_map=gap_map,
                weighted_gap_total=weighted_gap_total,
                critical_gap_total=critical_gap_total,
                records=records,
                effective=effective,
            )
            candidates.append(candidate)

        if gaps and not any(
            any(gain.skill_id in gap_map for gain in event.develops_skills)
            for event in self.bundle.events.values()
            if not event.mandatory
        ):
            reasons["catalog_gap"] += 1

        candidates.sort(key=lambda item: (-item.score, item.event_id))
        return self._diversify(candidates), reasons

    @staticmethod
    def _candidate_kind(
        employee: Employee,
        target_profile: RoleProfile,
        event: DevelopmentEvent,
    ) -> str | None:
        if employee.role in event.target_roles and employee.grade in event.target_grades:
            return "current_role"
        target_index = GRADE_ORDER.index(target_profile.grade)
        current_index = GRADE_ORDER.index(employee.grade)
        if target_profile.role in event.target_roles and any(
            current_index < GRADE_ORDER.index(grade) <= target_index
            for grade in event.target_grades
        ):
            return "bridge"
        return None

    def _score_candidate(
        self,
        employee: Employee,
        event: DevelopmentEvent,
        kind: str,
        impacts: dict[str, int],
        gap_map: dict[str, SkillGap],
        weighted_gap_total: int,
        critical_gap_total: int,
        records: list[ActivityRecord],
        effective: dict[str, int],
    ) -> Recommendation:
        weighted_impact = sum(
            gain * (2 if gap_map[skill_id].critical else 1)
            for skill_id, gain in impacts.items()
        )
        critical_impact = sum(
            gain for skill_id, gain in impacts.items() if gap_map[skill_id].critical
        )
        values = {
            "gap_coverage": min(1.0, weighted_impact / max(1, weighted_gap_total)),
            "critical_coverage": (
                min(1.0, critical_impact / critical_gap_total)
                if critical_gap_total
                else 0.5
            ),
            "goal_alignment": 1.0 if kind == "current_role" else 0.9,
            "history_fit": self._history_fit(employee, event, records),
            "availability": self._availability(event),
            "effort_fit": self._effort_fit(event.duration_hours),
        }
        labels = {
            "gap_coverage": "Закрытие разрыва",
            "critical_coverage": "Критичные навыки",
            "goal_alignment": "Карьерная цель",
            "history_fit": "История участия",
            "availability": "Доступность",
            "effort_fit": "Трудозатраты",
        }
        factors = tuple(
            FactorScore(
                code=code,
                label=labels[code],
                value=round(values[code], 4),
                weight=weight,
                contribution=round(values[code] * weight, 4),
            )
            for code, weight in WEIGHTS.items()
        )
        score = round(sum(item.contribution for item in factors) * 100)
        primary_skill_id = max(
            impacts,
            key=lambda skill_id: (
                int(gap_map[skill_id].critical),
                impacts[skill_id],
                gap_map[skill_id].gap,
                skill_id,
            ),
        )
        primary_gap = gap_map[primary_skill_id]
        projected = effective.get(primary_skill_id, 0) + impacts[primary_skill_id]
        history_value = values["history_fit"]
        if history_value >= 0.6:
            history_reason = "История похожих активностей показывает хорошую завершаемость."
        elif history_value <= 0.4:
            history_reason = "История участия снижает приоритет, но не перекрывает карьерный разрыв."
        else:
            history_reason = "История участия учтена с нейтральным приоритетом."
        reasons = (
            f"{primary_gap.name} — {'критичный ' if primary_gap.critical else ''}навык для {self._target_label(employee)}.",
            f"Ожидаемый эффект: {primary_gap.current_level} → {projected} при требовании {primary_gap.required_level}.",
            history_reason,
        )
        return Recommendation(
            event_id=event.event_id,
            title=event.title,
            event_format=event.event_format,
            duration_hours=event.duration_hours,
            score=score,
            kind="bridge" if kind == "bridge" else "current_role",
            skill=primary_gap.name,
            current_level=primary_gap.current_level,
            projected_level=projected,
            required_level=primary_gap.required_level,
            reasons=reasons,
            factors=factors,
        )

    @staticmethod
    def _target_label(employee: Employee) -> str:
        if employee.career_goal:
            return f"цели {employee.career_goal.target_role} {employee.career_goal.target_grade}"
        index = GRADE_ORDER.index(employee.grade)
        if index < len(GRADE_ORDER) - 1:
            return f"перехода на {GRADE_ORDER[index + 1]}"
        return "текущего Lead-профиля"

    def _history_fit(
        self,
        employee: Employee,
        event: DevelopmentEvent,
        records: list[ActivityRecord],
    ) -> float:
        status_value = {
            "completed": 1.0,
            "in_progress": 0.6,
            "dropped": 0.0,
            "no_show": 0.0,
            "declined": 0.25,
            "overdue": 0.3,
        }
        weighted_total = 0.0
        weighted_value = 0.0
        for record in records:
            historic_event = self.bundle.events.get(record.event_id)
            if historic_event is None or historic_event.mandatory:
                continue
            same_type = historic_event.event_type == event.event_type
            same_format = historic_event.event_format == event.event_format
            if not same_type and not same_format:
                continue
            similarity = 1.0 if same_type and same_format else 0.65
            age_days = max(0, (self.bundle.as_of_date - record.activity_date).days)
            recency = math.pow(0.5, age_days / 730)
            weight = similarity * recency
            value = status_value[record.status]
            if record.status == "declined" and record.assigned_by in {"manager", "hr"}:
                value = 0.4
            weighted_total += weight
            weighted_value += weight * value
        if not weighted_total:
            return 0.5
        return max(0.0, min(1.0, (1.0 + weighted_value) / (2.0 + weighted_total)))

    def _availability(self, event: DevelopmentEvent) -> float:
        if event.event_format == "self_paced":
            return 1.0
        future = [item for item in event.upcoming_sessions if item >= self.bundle.as_of_date]
        if not future:
            return 0.0
        days = (min(future) - self.bundle.as_of_date).days
        return 1.0 if days <= 30 else 0.8 if days <= 60 else 0.6

    @staticmethod
    def _effort_fit(hours: float) -> float:
        if hours <= 8:
            return 1.0
        if hours <= 16:
            return 0.8
        if hours <= 24:
            return 0.6
        return 0.4

    @staticmethod
    def _diversify(candidates: list[Recommendation]) -> list[Recommendation]:
        selected: list[Recommendation] = []
        remaining = list(candidates)
        while remaining and len(selected) < 3:
            def adjusted(item: Recommendation) -> tuple[float, str]:
                similarity = 0.0
                for chosen in selected:
                    current = 0.0
                    if item.skill == chosen.skill:
                        current += 0.7
                    if item.event_format == chosen.event_format:
                        current += 0.2
                    if item.kind == chosen.kind:
                        current += 0.1
                    similarity = max(similarity, current)
                return item.score / 100 - 0.12 * similarity, item.event_id

            best = max(remaining, key=lambda item: (adjusted(item)[0], -int(item.event_id.split("_")[-1])))
            selected.append(best)
            remaining.remove(best)
        return selected
