from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class EmployeeListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    employee_id: str
    full_name: str
    department: str
    role: str
    grade: str


class EmployeeResponse(EmployeeListItemResponse):
    work_format: str
    preferred_language: str


class ProgressResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    current_points: int
    required_points: int
    percentage: int = Field(ge=0, le=100)


class SkillGapResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_id: str
    name: str
    current_level: int
    required_level: int
    gap: int
    critical: bool


class FactorScoreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    label: str
    value: float = Field(ge=0, le=1)
    weight: float = Field(ge=0, le=1)
    contribution: float = Field(ge=0, le=1)


class RecommendationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    title: str
    event_format: Literal["online", "offline", "self_paced"]
    duration_hours: float
    score: int = Field(ge=0, le=100)
    kind: Literal["current_role", "bridge"]
    skill: str
    current_level: int
    projected_level: int
    required_level: int
    reasons: tuple[str, ...] = Field(min_length=3)
    factors: tuple[FactorScoreResponse, ...]


class ContinuationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    title: str
    completion_pct: int


class EmployeeJourneyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: Literal["dataset"]
    dataset_version: str
    as_of_date: date
    employee: EmployeeResponse
    target_role: str
    target_grade: str
    target_reason: str
    progress: ProgressResponse
    skill_gaps: tuple[SkillGapResponse, ...]
    recommendations: tuple[RecommendationResponse, ...]
    continuations: tuple[ContinuationResponse, ...]
    recommendation_mode: Literal["deterministic", "ai"]
    recommendation_notice: str | None
    primary_reason: str | None
    reason_counts: dict[str, int]


class SkillChangeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_id: str
    name: str
    before: int
    after: int
    applied_gain: int


class CompletionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    record_id: str
    idempotent_replay: bool
    changes: tuple[SkillChangeResponse, ...]
    journey: EmployeeJourneyResponse
