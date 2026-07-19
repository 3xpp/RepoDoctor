from __future__ import annotations

import os
import stat
import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from repo_doctor.checks import DEFAULT_CHECK_IDS, DEFAULT_CHECKS
from repo_doctor.checks.base import Check
from repo_doctor.checks.filesystem import is_protected_path
from repo_doctor.models import Severity
from repo_doctor.path_safety import has_symlink_component, normalize_local_path

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


def _format_validation_error(error: ValidationError) -> str:
    first = error.errors(include_input=False, include_url=False)[0]
    location = ".".join(str(part) for part in first["loc"]) or "configuration"
    message = str(first.get("msg", "invalid value"))
    return f"{location}: {message}"


def _reject_protected_config_path(path: Path) -> None:
    if is_protected_path(path):
        raise ConfigError(f"refusing to read protected configuration path: {path}")


def _read_bounded_config(path: Path) -> bytes:
    _reject_protected_config_path(path)
    try:
        if has_symlink_component(path):
            raise ConfigError(f"refusing to read configuration through a symbolic link: {path}")
        metadata = path.lstat()
    except FileNotFoundError as error:
        raise ConfigError(f"configuration file does not exist: {path}") from error
    except ConfigError:
        raise
    except OSError as error:
        raise ConfigError(f"configuration file cannot be accessed: {path}") from error
    if not stat.S_ISREG(metadata.st_mode):
        raise ConfigError(f"configuration path is not a regular file: {path}")
    if metadata.st_size > MAX_CONFIG_BYTES:
        raise ConfigError(f"configuration file is larger than 1 MiB: {path}")

    flags = os.O_RDONLY
    flags |= getattr(os, "O_BINARY", 0)
    flags |= getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    try:
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise ConfigError(f"configuration path is not a regular file: {path}")
        with os.fdopen(descriptor, "rb", closefd=True) as stream:
            descriptor = -1
            payload = stream.read(MAX_CONFIG_BYTES + 1)
    except ConfigError:
        raise
    except OSError as error:
        raise ConfigError(f"configuration file could not be read: {path}") from error
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(payload) > MAX_CONFIG_BYTES:
        raise ConfigError(f"configuration file is larger than 1 MiB: {path}")
    return payload


def _load_config_file(path: Path) -> RepoDoctorConfig:
    payload = _read_bounded_config(path)
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ConfigError(f"configuration file must be UTF-8: {path}") from error
    try:
        raw = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"configuration file contains invalid TOML: {path}") from error
    try:
        return RepoDoctorConfig.model_validate(raw)
    except ValidationError as error:
        detail = _format_validation_error(error)
        raise ConfigError(f"invalid configuration in {path}: {detail}") from error


def resolve_configuration(
    repo_root: Path,
    *,
    explicit_paths: Sequence[Path] = (),
) -> LoadedConfiguration:
    if len(explicit_paths) > 1:
        raise ConfigError("--config may be provided only once")
    if explicit_paths:
        try:
            candidate = normalize_local_path(explicit_paths[0], expand_user=True)
        except (OSError, RuntimeError) as error:
            raise ConfigError("configuration path cannot be normalized") from error
        return LoadedConfiguration(_load_config_file(candidate), candidate)

    candidate = repo_root / CONFIG_FILENAME
    _reject_protected_config_path(candidate)
    try:
        if has_symlink_component(candidate):
            raise ConfigError(
                f"refusing to read configuration through a symbolic link: {candidate}"
            )
        candidate.lstat()
    except FileNotFoundError:
        return LoadedConfiguration(DEFAULT_CONFIG, None)
    except ConfigError:
        raise
    except OSError as error:
        raise ConfigError(f"configuration file cannot be accessed: {candidate}") from error
    return LoadedConfiguration(_load_config_file(candidate), candidate)
