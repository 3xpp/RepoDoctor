from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from repo_doctor.checks import DEFAULT_CHECK_IDS, DEFAULT_CHECKS
from repo_doctor.checks.base import Check
from repo_doctor.models import Severity

CONFIG_FILENAME = ".repo-doctor.toml"
CONFIG_VERSION: Literal[1] = 1
MAX_CONFIG_BYTES = 1024 * 1024


class ConfigError(ValueError):
    """Raised when repository configuration cannot be selected or validated."""


class CheckSettings(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        hide_input_in_errors=True,
        strict=True,
        validate_default=True,
    )

    enabled: bool = True


class ScoringSettings(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        hide_input_in_errors=True,
        strict=True,
        validate_default=True,
    )

    high: int = Field(default=20, ge=0, le=100)
    medium: int = Field(default=10, ge=0, le=100)
    low: int = Field(default=5, ge=0, le=100)
    info: int = Field(default=0, ge=0, le=100)

    @model_validator(mode="after")
    def preserve_severity_order(self) -> Self:
        if self.info != 0:
            raise ValueError("info deduction must be 0")
        if not self.high >= self.medium >= self.low >= self.info:
            raise ValueError("deductions must satisfy high >= medium >= low >= info")
        return self


class RepoDoctorConfig(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        hide_input_in_errors=True,
        strict=True,
        validate_default=True,
    )

    version: Literal[1]
    scoring: ScoringSettings = Field(default_factory=ScoringSettings)
    checks: Mapping[str, CheckSettings] = Field(default_factory=dict)

    @field_validator("version", mode="before")
    @classmethod
    def require_integer_version(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("version must be an integer")
        return value

    @field_validator("checks")
    @classmethod
    def validate_and_freeze_checks(
        cls, value: Mapping[str, CheckSettings]
    ) -> Mapping[str, CheckSettings]:
        unknown = sorted(set(value) - set(DEFAULT_CHECK_IDS))
        if unknown:
            raise ValueError(f"unknown check id: {unknown[0]}")
        return MappingProxyType(dict(value))

    @model_validator(mode="after")
    def require_enabled_check(self) -> Self:
        if not any(self.is_enabled(check_id) for check_id in DEFAULT_CHECK_IDS):
            raise ValueError("at least one check must remain enabled")
        return self

    def is_enabled(self, check_id: str) -> bool:
        settings = self.checks.get(check_id)
        return True if settings is None else settings.enabled


@dataclass(frozen=True, slots=True)
class LoadedConfiguration:
    settings: RepoDoctorConfig
    source_path: Path | None


DEFAULT_CONFIG = RepoDoctorConfig(version=CONFIG_VERSION)


def enabled_check_ids(settings: RepoDoctorConfig) -> tuple[str, ...]:
    return tuple(check_id for check_id in DEFAULT_CHECK_IDS if settings.is_enabled(check_id))


def select_checks(
    settings: RepoDoctorConfig,
    registry: Sequence[Check] = DEFAULT_CHECKS,
) -> tuple[Check, ...]:
    return tuple(check for check in registry if settings.is_enabled(check.id))


def severity_deductions(settings: RepoDoctorConfig) -> Mapping[Severity, int]:
    return MappingProxyType(
        {
            Severity.HIGH: settings.scoring.high,
            Severity.MEDIUM: settings.scoring.medium,
            Severity.LOW: settings.scoring.low,
            Severity.INFO: settings.scoring.info,
        }
    )
