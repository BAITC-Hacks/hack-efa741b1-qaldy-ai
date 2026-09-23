from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ImportValidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    employees_json: dict[str, Any]
    activity_history_csv: str | None = Field(default=None, max_length=10_000_000)


class ImportIssueResponse(BaseModel):
    file: str
    location: str
    code: str
    reason: str


class ImportValidationResponse(BaseModel):
    valid: bool
    validation_token: str | None
    package_hash: str | None
    expires_at: datetime | None
    counts: dict[str, int]
    preview: dict[str, int]
    errors: tuple[ImportIssueResponse, ...]
    warnings: tuple[ImportIssueResponse, ...]


class ImportApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    validation_token: str = Field(min_length=1, max_length=128)
    package_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class ImportApplyResponse(BaseModel):
    batch_id: str
    package_hash: str
    inserted_employees: int
    inserted_history: int
    no_op_employees: int
    no_op_history: int
    idempotent_replay: bool
