from typing import Literal

from pydantic import BaseModel, Field


class EmployeeSummary(BaseModel):
    employee_id: str
    full_name: str
    role: str
    grade: str
    target_role: str
    target_grade: str
    trajectory_progress: int = Field(ge=0, le=100)


class SkillGap(BaseModel):
    skill_id: str
    name: str
    current_level: int = Field(ge=0, le=5)
    required_level: int = Field(ge=0, le=5)
    critical: bool


class Recommendation(BaseModel):
    event_id: str
    title: str
    format: Literal["online", "offline", "self_paced"]
    duration_hours: float = Field(gt=0)
    score: int = Field(ge=0, le=100)
    skill: str
    current_level: int = Field(ge=0, le=5)
    projected_level: int = Field(ge=0, le=5)
    required_level: int = Field(ge=0, le=5)
    reasons: list[str] = Field(min_length=3)


class EmployeeJourney(BaseModel):
    source: Literal["demo", "dataset"]
    employee: EmployeeSummary
    skill_gaps: list[SkillGap]
    recommendations: list[Recommendation] = Field(max_length=3)
