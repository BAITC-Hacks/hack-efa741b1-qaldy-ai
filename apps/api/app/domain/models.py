from dataclasses import dataclass, field
from datetime import date
from typing import Literal

Grade = Literal["Junior", "Middle", "Senior", "Lead"]
ActivityStatus = Literal[
    "completed", "in_progress", "dropped", "no_show", "declined", "overdue"
]


@dataclass(frozen=True)
class CareerGoal:
    target_role: str
    target_grade: Grade


@dataclass(frozen=True)
class Employee:
    employee_id: str
    full_name: str
    department: str
    role: str
    grade: Grade
    work_format: str
    preferred_language: str
    career_goal: CareerGoal | None
    skills: dict[str, int]
    last_review_date: date


@dataclass(frozen=True)
class Skill:
    skill_id: str
    name: str
    skill_type: str
    category: str


@dataclass(frozen=True)
class RoleProfile:
    role: str
    grade: Grade
    required_skills: dict[str, int]
    critical_skills: frozenset[str]


@dataclass(frozen=True)
class SkillGain:
    skill_id: str
    gain: int
    max_level: int


@dataclass(frozen=True)
class DevelopmentEvent:
    event_id: str
    title: str
    event_type: str
    event_format: str
    duration_hours: float
    mandatory: bool
    repeatable: bool
    target_roles: frozenset[str]
    target_grades: frozenset[Grade]
    develops_skills: tuple[SkillGain, ...]
    prerequisites: dict[str, int]
    upcoming_sessions: tuple[date, ...]


@dataclass(frozen=True)
class ActivityRecord:
    record_id: str
    employee_id: str
    event_id: str
    activity_date: date
    status: ActivityStatus
    completion_pct: int
    assigned_by: str
    source: Literal["seed", "overlay"] = "seed"


@dataclass(frozen=True)
class DatasetBundle:
    dataset_version: str
    as_of_date: date
    employees: dict[str, Employee]
    skills: dict[str, Skill]
    role_profiles: dict[tuple[str, Grade], RoleProfile]
    events: dict[str, DevelopmentEvent]
    history: tuple[ActivityRecord, ...]


@dataclass(frozen=True)
class SkillGap:
    skill_id: str
    name: str
    current_level: int
    required_level: int
    gap: int
    critical: bool


@dataclass(frozen=True)
class FactorScore:
    code: str
    label: str
    value: float
    weight: float
    contribution: float


@dataclass(frozen=True)
class Recommendation:
    event_id: str
    title: str
    event_format: str
    duration_hours: float
    score: int
    kind: Literal["current_role", "bridge"]
    skill: str
    current_level: int
    projected_level: int
    required_level: int
    reasons: tuple[str, ...]
    factors: tuple[FactorScore, ...]


@dataclass(frozen=True)
class Continuation:
    event_id: str
    title: str
    completion_pct: int


@dataclass(frozen=True)
class ProgressMetric:
    current_points: int
    required_points: int
    percentage: int


@dataclass(frozen=True)
class EmployeeJourney:
    source: Literal["dataset"]
    dataset_version: str
    as_of_date: date
    employee: Employee
    target_role: str
    target_grade: Grade
    target_reason: str
    progress: ProgressMetric
    skill_gaps: tuple[SkillGap, ...]
    recommendations: tuple[Recommendation, ...]
    continuations: tuple[Continuation, ...]
    recommendation_mode: Literal["deterministic", "ai"] = "deterministic"
    recommendation_notice: str | None = None
    primary_reason: str | None = None
    reason_counts: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class SkillChange:
    skill_id: str
    name: str
    before: int
    after: int
    applied_gain: int


@dataclass(frozen=True)
class CompletionResult:
    record_id: str
    idempotent_replay: bool
    changes: tuple[SkillChange, ...]
    journey: EmployeeJourney
