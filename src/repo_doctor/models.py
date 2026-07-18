from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, field_validator


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Finding(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    title: str
    description: str
    severity: Severity
    category: str
    recommendation: str
    passed: bool


class Report(BaseModel):
    model_config = ConfigDict(frozen=True)

    repo_path: str
    score: int
    max_score: int
    summary: str
    findings: tuple[Finding, ...]
    generated_at: datetime
    version: str

    @field_validator("generated_at")
    @classmethod
    def require_aware_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("generated_at must be timezone-aware")
        return value.astimezone(UTC)
