from datetime import date
from typing import Any

from pydantic import BaseModel, Field


class HRFilterResponse(BaseModel):
    department: str | None = None
    role: str | None = None
    grade: str | None = None


class HRBaseResponse(BaseModel):
    dataset_version: str
    as_of_date: date
    filters: HRFilterResponse
    employee_count: int = Field(ge=0)


class SkillGapAggregate(BaseModel):
    skill_id: str
    name: str
    affected_employees: int = Field(ge=0)
    total_gap: int = Field(ge=0)
    critical_employees: int = Field(ge=0)
    average_gap: float = Field(ge=0)


class SkillGapsResponse(HRBaseResponse):
    items: list[SkillGapAggregate]


class ParticipationGroup(BaseModel):
    key: str
    title: str | None = None
    total: int = Field(ge=0)
    completed: int = Field(ge=0)
    completion_rate: float = Field(ge=0, le=1)
    statuses: dict[str, int]


class ParticipationResponse(HRBaseResponse):
    items: list[Any]
    total_records: int = Field(ge=0)
    participating_employees: int = Field(ge=0)
    statuses: dict[str, int]
    by_type: list[ParticipationGroup]
    by_event: list[ParticipationGroup]


class UncoveredEmployee(BaseModel):
    employee_id: str
    full_name: str
    department: str
    role: str
    grade: str
    primary_reason: str
    reason_counts: dict[str, int]
    gap_count: int = Field(ge=0)


class UncoveredEmployeesResponse(HRBaseResponse):
    items: list[UncoveredEmployee]


class CatalogGap(BaseModel):
    skill_id: str
    name: str
    affected_employees: int = Field(ge=0)
    critical_employees: int = Field(ge=0)
    roles: list[str]


class CatalogGapsResponse(HRBaseResponse):
    items: list[CatalogGap]
