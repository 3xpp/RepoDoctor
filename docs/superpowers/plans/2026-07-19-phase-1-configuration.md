# Phase 1 Repository Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a safe, versioned `.repo-doctor.toml` policy that configures enabled checks and severity deductions through automatic discovery or `--config`.

**Architecture:** A new configuration domain parses strict TOML into frozen Pydantic settings, returns the effective source path, and filters the ordered check registry. The CLI resolves the repository, selects one policy, injects checks, deductions, and content exclusions into the scanner, then renders the unchanged report shape. Configuration files are bounded, symlink-safe, protected from report overwrites, and never echoed through validation errors.

**Tech Stack:** Python 3.12+, standard-library `tomllib`, `pathlib`, `os`, and `stat`; Pydantic 2; Typer; pytest; Ruff; mypy; uv.

---

## Source specification

Implement [the approved Phase 1 design](../specs/2026-07-19-phase-1-configuration-design.md). Preserve these invariants throughout every task:

- No new runtime dependency.
- No remote access, repository rewriting, or secret-file reads.
- No `.env`, credential, or private-key fixture content.
- No report-model field additions or reordering.
- No disabled check execution or synthetic passed findings.
- No config-table ordering in reports; registry order remains authoritative.
- Neither the active policy nor the reserved root policy is read by environment
  detection.
- No raw TOML or Pydantic input values in errors.
- Every implementation milestone is tested before its conventional commit.
- No push.

## File responsibility map

### New files

- `src/repo_doctor/config.py` — strict configuration models, safe TOML loading,
  discovery precedence, enabled-check selection, and deduction conversion.
- `src/repo_doctor/path_safety.py` — lexical absolute-path normalization and
  symbolic-link-component detection shared by config and report output handling.
- `tests/unit/test_check_registry.py` — stable ID, protocol, uniqueness, and registry
  order contract.
- `tests/unit/test_config_models.py` — strict schema, default inheritance, ordering,
  and immutable settings contract.
- `tests/unit/test_config_loading.py` — discovery, precedence, bounded reads,
  symlink/non-regular rejection, protected-path behavior, and sanitized errors.
- `.repo-doctor.toml` — canonical version-1 repository policy with all Phase 0
  defaults enabled.

### Modified source and tests

- `src/repo_doctor/checks/base.py:8-11` — add stable IDs and content exclusions to
  the protocol.
- `src/repo_doctor/checks/__init__.py:9-17` — publish exact ordered IDs and enforce
  uniqueness.
- `src/repo_doctor/checks/readme.py:102-151`, `license.py:21-45`, `tests.py:21-45`,
  `ci.py:6-40`, `docker.py:16-42`, `env_example.py:57-123` — expose IDs, accept
  exclusions, and return matching finding IDs; the environment check consumes the
  exclusions.
- `src/repo_doctor/scoring.py:1-21` — make default deductions immutable and allow a
  complete injected mapping.
- `src/repo_doctor/scanner.py:13-49` — expose repository resolution and inject
  checks, deductions, and excluded content paths.
- `src/repo_doctor/cli.py:1-139` — add repeated-option detection, configuration
  resolution, safe output collisions, and configured scanning.
- `tests/unit/test_scoring.py`, `test_scanner.py`, `test_env_example_check.py`, and
  `test_cli.py` — verify configured scoring, orchestration, exclusions, CLI errors,
  output protection, and compatibility.
- `tests/e2e/test_scan_fixtures.py` — prove exact default fixture scores and a
  configured end-to-end scan.
- `src/repo_doctor/__init__.py`, `pyproject.toml`, `uv.lock`, and
  `tests/unit/conftest.py` — advance the package/report version to `0.2.0`.
- `README.md`, `docs/SCORING.md`, `docs/DECISIONS.md`, and `AGENTS.md` — document the
  configuration contract and contributor obligations.
- `docs/FAILURES.md` — change only if implementation or validation produces a new
  concrete failure not already covered by its existing sandbox entries.

## Task 1: Give every check a stable pre-run identity

**Files:**

- Create: `tests/unit/test_check_registry.py`
- Modify: `src/repo_doctor/checks/base.py:1-11`
- Modify: `src/repo_doctor/checks/__init__.py:1-17`
- Modify: `src/repo_doctor/checks/readme.py:102-151`
- Modify: `src/repo_doctor/checks/license.py:21-45`
- Modify: `src/repo_doctor/checks/tests.py:21-45`
- Modify: `src/repo_doctor/checks/ci.py:6-40`
- Modify: `src/repo_doctor/checks/docker.py:16-42`
- Modify: `src/repo_doctor/checks/env_example.py:97-123`

- [ ] **Step 1: Write the failing registry-contract tests**

Create `tests/unit/test_check_registry.py` with the exact ordered contract and a
runtime call that proves each finding reuses its check ID:

```python
from pathlib import Path

import pytest

from repo_doctor.checks import DEFAULT_CHECKS, DEFAULT_CHECK_IDS
from repo_doctor.checks.base import Check

EXPECTED_CHECK_IDS = (
    "readme-exists",
    "readme-sections",
    "license-exists",
    "tests-exist",
    "ci-exists",
    "docker-exists",
    "env-example",
)


def test_default_check_ids_are_exact_ordered_and_unique() -> None:
    assert DEFAULT_CHECK_IDS == EXPECTED_CHECK_IDS
    assert len(set(DEFAULT_CHECK_IDS)) == len(DEFAULT_CHECK_IDS)


def test_default_checks_satisfy_protocol_and_reuse_ids(tmp_path: Path) -> None:
    for check in DEFAULT_CHECKS:
        assert isinstance(check, Check)
        finding = check.run(tmp_path, excluded_paths=frozenset())
        assert finding.id == check.id


def test_default_check_ids_are_read_only() -> None:
    for check in DEFAULT_CHECKS:
        with pytest.raises(AttributeError):
            setattr(check, "id", "changed")
```

- [ ] **Step 2: Run the registry test and verify red state**

Run: `uv run pytest tests/unit/test_check_registry.py -v`

Expected: collection fails because `DEFAULT_CHECK_IDS` does not exist, proving the
test precedes the implementation.

- [ ] **Step 3: Extend the protocol with ID and exclusion contracts**

Replace the `Check` protocol body in `src/repo_doctor/checks/base.py` with:

```python
@runtime_checkable
class Check(Protocol):
    @property
    def id(self) -> str:
        """Return the stable finding ID before the check runs."""
        raise NotImplementedError

    def run(
        self,
        repo_path: Path,
        *,
        excluded_paths: frozenset[Path] = frozenset(),
    ) -> Finding:
        """Evaluate one deterministic repository-readiness rule."""
        raise NotImplementedError
```

- [ ] **Step 4: Add the exact IDs and compatible signatures to all implementations**

Add the following read-only properties inside the named classes:

```python
# ReadmeExistsCheck
@property
def id(self) -> str:
    return "readme-exists"

# ReadmeSectionsCheck
@property
def id(self) -> str:
    return "readme-sections"

# LicenseCheck
@property
def id(self) -> str:
    return "license-exists"

# TestsCheck
@property
def id(self) -> str:
    return "tests-exist"

# GitHubActionsCheck
@property
def id(self) -> str:
    return "ci-exists"

# DockerCheck
@property
def id(self) -> str:
    return "docker-exists"

# EnvExampleCheck
@property
def id(self) -> str:
    return "env-example"
```

Change every existing check method to this exact compatible signature:

```python
def run(
    self,
    repo_path: Path,
    *,
    excluded_paths: frozenset[Path] = frozenset(),
) -> Finding:
```

Keep each existing check body unchanged in this task. In every returned `Finding`,
replace only the existing literal ID argument with `id=self.id`; leave all other
arguments unchanged. The six checks that do not yet consume `excluded_paths`
intentionally accept the immutable keyword so the scanner can call the protocol
uniformly.

- [ ] **Step 5: Publish and guard the ordered ID tuple**

Append this immediately after `DEFAULT_CHECKS` in
`src/repo_doctor/checks/__init__.py`:

```python
DEFAULT_CHECK_IDS = tuple(check.id for check in DEFAULT_CHECKS)
if len(set(DEFAULT_CHECK_IDS)) != len(DEFAULT_CHECK_IDS):
    raise RuntimeError("default check IDs must be unique")
```

- [ ] **Step 6: Run focused and existing check tests**

Run: `uv run pytest tests/unit/test_check_registry.py tests/unit/test_readme_check.py tests/unit/test_license_check.py tests/unit/test_repository_checks.py tests/unit/test_env_example_check.py -v`

Expected: all selected tests pass; check results and Phase 0 behavior are unchanged.

- [ ] **Step 7: Commit stable check identities**

```bash
git add src/repo_doctor/checks tests/unit/test_check_registry.py
git commit -m "refactor: add stable check identifiers"
```

## Task 2: Add strict immutable configuration models

**Files:**

- Create: `src/repo_doctor/config.py`
- Create: `tests/unit/test_config_models.py`

- [ ] **Step 1: Write the failing model tests**

Create `tests/unit/test_config_models.py` with these representative assertions; use
parameterization for every listed invalid shape rather than duplicating setup:

```python
from collections.abc import Mapping

import pytest
from pydantic import ValidationError

from repo_doctor.config import (
    DEFAULT_CONFIG,
    CheckSettings,
    RepoDoctorConfig,
    ScoringSettings,
    enabled_check_ids,
    select_checks,
    severity_deductions,
)
from repo_doctor.models import Severity


def test_builtin_configuration_matches_phase_zero() -> None:
    assert DEFAULT_CONFIG.version == 1
    assert enabled_check_ids(DEFAULT_CONFIG) == (
        "readme-exists",
        "readme-sections",
        "license-exists",
        "tests-exist",
        "ci-exists",
        "docker-exists",
        "env-example",
    )
    assert severity_deductions(DEFAULT_CONFIG) == {
        Severity.HIGH: 20,
        Severity.MEDIUM: 10,
        Severity.LOW: 5,
        Severity.INFO: 0,
    }


def test_version_is_required() -> None:
    with pytest.raises(ValidationError):
        RepoDoctorConfig.model_validate({})


def test_canonical_full_configuration_matches_builtins() -> None:
    checks = {
        check_id: {"enabled": True}
        for check_id in enabled_check_ids(DEFAULT_CONFIG)
    }
    config = RepoDoctorConfig.model_validate(
        {
            "version": 1,
            "scoring": {"high": 20, "medium": 10, "low": 5, "info": 0},
            "checks": checks,
        }
    )
    assert enabled_check_ids(config) == enabled_check_ids(DEFAULT_CONFIG)
    assert severity_deductions(config) == severity_deductions(DEFAULT_CONFIG)


def test_partial_configuration_inherits_defaults_independently() -> None:
    config = RepoDoctorConfig.model_validate(
        {"version": 1, "checks": {"docker-exists": {"enabled": False}}}
    )
    assert "docker-exists" not in enabled_check_ids(config)
    assert "readme-exists" in enabled_check_ids(config)
    assert "readme-sections" in enabled_check_ids(config)
    assert config.scoring == ScoringSettings()


@pytest.mark.parametrize("version", [True, "1", 0, 2])
def test_version_is_strict_integer_one(version: object) -> None:
    with pytest.raises(ValidationError):
        RepoDoctorConfig.model_validate({"version": version})


@pytest.mark.parametrize(
    "payload",
    [
        {"version": 1, "unknown": True},
        {"version": 1, "scoring": {"unknown": 5}},
        {"version": 1, "checks": {"unknown-check": {"enabled": True}}},
        {"version": 1, "checks": {"docker-exists": {"unknown": True}}},
        {"version": 1, "checks": []},
        {"version": 1, "scoring": []},
    ],
)
def test_unknown_keys_and_wrong_table_shapes_are_rejected(payload: object) -> None:
    with pytest.raises(ValidationError):
        RepoDoctorConfig.model_validate(payload)


@pytest.mark.parametrize("enabled", [0, 1, "true"])
def test_enabled_requires_toml_boolean(enabled: object) -> None:
    with pytest.raises(ValidationError):
        CheckSettings.model_validate({"enabled": enabled})


@pytest.mark.parametrize("value", [True, 1.5, "20", -1, 101])
def test_deductions_are_strict_bounded_integers(value: object) -> None:
    with pytest.raises(ValidationError):
        ScoringSettings.model_validate({"high": value})


@pytest.mark.parametrize(
    "payload",
    [
        {"info": 1},
        {"high": 9, "medium": 10},
        {"medium": 4, "low": 5},
        {"low": -1},
    ],
)
def test_severity_meaning_constraints_are_enforced(payload: dict[str, int]) -> None:
    with pytest.raises(ValidationError):
        ScoringSettings.model_validate(payload)


def test_all_checks_disabled_is_rejected() -> None:
    checks = {
        check_id: {"enabled": False}
        for check_id in enabled_check_ids(DEFAULT_CONFIG)
    }
    with pytest.raises(ValidationError, match="at least one check"):
        RepoDoctorConfig.model_validate({"version": 1, "checks": checks})


def test_configuration_mappings_are_read_only() -> None:
    config = RepoDoctorConfig.model_validate(
        {"version": 1, "checks": {"docker-exists": {"enabled": False}}}
    )
    assert isinstance(config.checks, Mapping)
    with pytest.raises(TypeError):
        config.checks["docker-exists"] = CheckSettings(enabled=True)  # type: ignore[index]
```

Add these positive and isolation tests in the same file:

```python
def test_zero_deductions_are_valid_when_monotonic() -> None:
    settings = ScoringSettings(high=0, medium=0, low=0, info=0)
    assert settings.high == settings.medium == settings.low == settings.info == 0


def test_custom_configuration_does_not_mutate_defaults() -> None:
    custom = RepoDoctorConfig.model_validate(
        {
            "version": 1,
            "scoring": {"high": 30},
            "checks": {"docker-exists": {"enabled": False}},
        }
    )
    assert custom.scoring.high == 30
    assert custom.is_enabled("docker-exists") is False
    assert DEFAULT_CONFIG.scoring.high == 20
    assert DEFAULT_CONFIG.is_enabled("docker-exists") is True
```

- [ ] **Step 2: Run the model tests and verify red state**

Run: `uv run pytest tests/unit/test_config_models.py -v`

Expected: collection fails because `repo_doctor.config` does not exist.

- [ ] **Step 3: Implement the strict schema and derived values**

Create `src/repo_doctor/config.py` with this model layer:

```python
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
CONFIG_VERSION = 1
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
```

- [ ] **Step 4: Run model tests, Ruff, and mypy**

Run: `uv run pytest tests/unit/test_config_models.py -v`

Expected: every configuration-model test passes.

Run: `uv run ruff check src/repo_doctor/config.py tests/unit/test_config_models.py`

Expected: exit 0 with no diagnostics.

Run: `uv run mypy src/repo_doctor/config.py`

Expected: exit 0 with no typing errors.

- [ ] **Step 5: Commit the model layer**

```bash
git add src/repo_doctor/config.py tests/unit/test_config_models.py
git commit -m "feat: add strict repository configuration models"
```

## Task 3: Load one configuration safely and deterministically

**Files:**

- Create: `src/repo_doctor/path_safety.py`
- Create: `tests/unit/test_config_loading.py`
- Modify: `src/repo_doctor/config.py`

- [ ] **Step 1: Write discovery and precedence tests**

Add these test shapes to `tests/unit/test_config_loading.py`:

```python
import os
import stat
from pathlib import Path

import pytest

import repo_doctor.config as config_module
from repo_doctor.config import (
    CONFIG_FILENAME,
    DEFAULT_CONFIG,
    MAX_CONFIG_BYTES,
    ConfigError,
    resolve_configuration,
)


def test_missing_automatic_config_uses_builtins(tmp_path: Path) -> None:
    loaded = resolve_configuration(tmp_path)
    assert loaded.settings == DEFAULT_CONFIG
    assert loaded.source_path is None


def test_automatic_config_is_discovered_and_inherits_defaults(tmp_path: Path) -> None:
    policy = tmp_path / CONFIG_FILENAME
    policy.write_text(
        "version = 1\n[checks.docker-exists]\nenabled = false\n",
        encoding="utf-8",
    )
    loaded = resolve_configuration(tmp_path)
    assert loaded.source_path == policy
    assert loaded.settings.is_enabled("docker-exists") is False
    assert loaded.settings.is_enabled("readme-exists") is True


def test_explicit_config_skips_automatic_candidate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    automatic = tmp_path / CONFIG_FILENAME
    explicit = tmp_path / "policy.toml"
    explicit.write_text("version = 1\n", encoding="utf-8")
    original_lstat = Path.lstat

    def guarded_lstat(path: Path):
        if path == automatic:
            raise AssertionError("automatic candidate was inspected")
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", guarded_lstat)
    loaded = resolve_configuration(tmp_path, explicit_paths=(explicit,))
    assert loaded.source_path == explicit


def test_duplicate_explicit_options_fail_before_file_access(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="only once"):
        resolve_configuration(
            tmp_path,
            explicit_paths=(tmp_path / "one.toml", tmp_path / "two.toml"),
        )
```

Add these path-resolution tests without changing a process home environment variable:

```python
def test_relative_explicit_path_uses_process_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = tmp_path / "policy.toml"
    policy.write_text("version = 1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    loaded = resolve_configuration(tmp_path, explicit_paths=(Path("policy.toml"),))
    assert loaded.source_path == policy


def test_explicit_path_expands_user_lexically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    requested = Path("~/policy.toml")
    policy = tmp_path / "policy.toml"
    policy.write_text("version = 1\n", encoding="utf-8")

    def fake_expanduser(path: Path) -> Path:
        assert path == requested
        return policy

    monkeypatch.setattr(Path, "expanduser", fake_expanduser)
    loaded = resolve_configuration(tmp_path, explicit_paths=(requested,))
    assert loaded.source_path == policy


def test_missing_explicit_config_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="does not exist"):
        resolve_configuration(
            tmp_path,
            explicit_paths=(tmp_path / "missing-policy.toml",),
        )
```

- [ ] **Step 2: Write bounded-read and safety tests**

Use only ordinary policy files and nonexistent protected paths. Add tests with these
exact assertions:

```python
def valid_policy_of_size(size: int) -> bytes:
    prefix = b"version = 1\n#"
    return prefix + (b"x" * (size - len(prefix) - 1)) + b"\n"


def test_exact_size_limit_is_accepted(tmp_path: Path) -> None:
    policy = tmp_path / "policy.toml"
    payload = valid_policy_of_size(MAX_CONFIG_BYTES)
    assert len(payload) == MAX_CONFIG_BYTES
    policy.write_bytes(payload)
    assert resolve_configuration(tmp_path, explicit_paths=(policy,)).settings.version == 1


def test_size_limit_plus_one_is_rejected(tmp_path: Path) -> None:
    policy = tmp_path / "policy.toml"
    policy.write_bytes(valid_policy_of_size(MAX_CONFIG_BYTES + 1))
    with pytest.raises(ConfigError, match="larger than 1 MiB"):
        resolve_configuration(tmp_path, explicit_paths=(policy,))


def test_protected_path_is_rejected_before_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    protected = tmp_path / "secrets.toml"

    def fail_open(*args: object, **kwargs: object) -> int:
        raise AssertionError("protected path was opened")

    monkeypatch.setattr(config_module.os, "open", fail_open)
    with pytest.raises(ConfigError, match="protected"):
        resolve_configuration(tmp_path, explicit_paths=(protected,))


def test_no_follow_flag_is_used_when_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if not hasattr(os, "O_NOFOLLOW"):
        pytest.skip("O_NOFOLLOW is not available")
    policy = tmp_path / "policy.toml"
    policy.write_text("version = 1\n", encoding="utf-8")
    real_open = os.open
    observed_flags = 0

    def recording_open(path: Path, flags: int) -> int:
        nonlocal observed_flags
        observed_flags = flags
        return real_open(path, flags)

    monkeypatch.setattr(config_module.os, "open", recording_open)
    resolve_configuration(tmp_path, explicit_paths=(policy,))
    assert observed_flags & os.O_NOFOLLOW


def test_validation_error_does_not_echo_input(tmp_path: Path) -> None:
    sentinel = "CONFIG_VALUE_MUST_NOT_LEAK"
    policy = tmp_path / "policy.toml"
    policy.write_text(
        f'version = 1\n[scoring]\nhigh = "{sentinel}"\n',
        encoding="utf-8",
    )
    with pytest.raises(ConfigError) as captured:
        resolve_configuration(tmp_path, explicit_paths=(policy,))
    message = str(captured.value)
    assert sentinel not in message
    assert "input_value" not in message
    assert "errors.pydantic.dev" not in message
```

Add the remaining file-safety tests with concrete failures:

```python
@pytest.mark.parametrize(
    ("payload", "message"),
    [(b"\xff", "UTF-8"), (b"version = [", "invalid TOML")],
)
def test_invalid_text_is_rejected(
    tmp_path: Path, payload: bytes, message: str
) -> None:
    policy = tmp_path / "policy.toml"
    policy.write_bytes(payload)
    with pytest.raises(ConfigError, match=message):
        resolve_configuration(tmp_path, explicit_paths=(policy,))


def test_directory_config_is_rejected(tmp_path: Path) -> None:
    policy = tmp_path / "policy.toml"
    policy.mkdir()
    with pytest.raises(ConfigError, match="regular file"):
        resolve_configuration(tmp_path, explicit_paths=(policy,))


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO files are not supported")
def test_fifo_config_is_rejected_before_open(tmp_path: Path) -> None:
    policy = tmp_path / "policy.toml"
    os.mkfifo(policy)
    with pytest.raises(ConfigError, match="regular file"):
        resolve_configuration(tmp_path, explicit_paths=(policy,))


@pytest.mark.parametrize("broken", [False, True])
def test_final_config_symlink_is_rejected(tmp_path: Path, broken: bool) -> None:
    target = tmp_path / ("missing.toml" if broken else "real.toml")
    if not broken:
        target.write_text("version = 1\n", encoding="utf-8")
    policy = tmp_path / "policy.toml"
    policy.symlink_to(target)
    with pytest.raises(ConfigError, match="symbolic link"):
        resolve_configuration(tmp_path, explicit_paths=(policy,))


@pytest.mark.parametrize("broken", [False, True])
def test_parent_config_symlink_is_rejected(tmp_path: Path, broken: bool) -> None:
    real_parent = tmp_path / ("missing-parent" if broken else "real-parent")
    if not broken:
        real_parent.mkdir()
        (real_parent / "policy.toml").write_text("version = 1\n", encoding="utf-8")
    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(real_parent, target_is_directory=True)
    with pytest.raises(ConfigError, match="symbolic link"):
        resolve_configuration(
            tmp_path,
            explicit_paths=(linked_parent / "policy.toml",),
        )


def test_inaccessible_metadata_is_translated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = tmp_path / "policy.toml"
    policy.write_text("version = 1\n", encoding="utf-8")
    original_lstat = Path.lstat

    def deny_target(path: Path):
        if path == policy:
            raise PermissionError("denied")
        return original_lstat(path)

    monkeypatch.setattr(Path, "lstat", deny_target)
    with pytest.raises(ConfigError, match="cannot be accessed"):
        resolve_configuration(tmp_path, explicit_paths=(policy,))


def test_open_failure_is_translated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = tmp_path / "policy.toml"
    policy.write_text("version = 1\n", encoding="utf-8")

    def deny_open(*args: object, **kwargs: object) -> int:
        raise PermissionError("denied")

    monkeypatch.setattr(config_module.os, "open", deny_open)
    with pytest.raises(ConfigError, match="could not be read"):
        resolve_configuration(tmp_path, explicit_paths=(policy,))


def test_opened_descriptor_must_be_regular(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = tmp_path / "policy.toml"
    policy.write_text("version = 1\n", encoding="utf-8")
    real_fstat = os.fstat

    def fake_fstat(descriptor: int) -> os.stat_result:
        values = list(real_fstat(descriptor))
        values[0] = stat.S_IFIFO
        return os.stat_result(values)

    monkeypatch.setattr(config_module.os, "fstat", fake_fstat)
    with pytest.raises(ConfigError, match="regular file"):
        resolve_configuration(tmp_path, explicit_paths=(policy,))


def test_bounded_read_rejects_growth_after_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = tmp_path / "policy.toml"
    policy.write_bytes(valid_policy_of_size(MAX_CONFIG_BYTES + 1))
    original_lstat = Path.lstat

    def stale_lstat(path: Path) -> os.stat_result:
        result = original_lstat(path)
        if path != policy:
            return result
        values = list(result)
        values[6] = MAX_CONFIG_BYTES
        return os.stat_result(values)

    monkeypatch.setattr(Path, "lstat", stale_lstat)
    with pytest.raises(ConfigError, match="larger than 1 MiB"):
        resolve_configuration(tmp_path, explicit_paths=(policy,))
```

- [ ] **Step 3: Run loader tests and verify red state**

Run: `uv run pytest tests/unit/test_config_loading.py -v`

Expected: tests fail because path-safety helpers and `resolve_configuration` are not
implemented.

- [ ] **Step 4: Implement shared lexical path safety**

Create `src/repo_doctor/path_safety.py`:

```python
import os
import stat
from pathlib import Path


def normalize_local_path(path: Path, *, expand_user: bool = False) -> Path:
    candidate = path.expanduser() if expand_user else path
    return Path(os.path.abspath(os.path.normpath(os.fspath(candidate))))


def has_symlink_component(path: Path) -> bool:
    candidate = Path(path.anchor)
    for part in path.parts[1:]:
        candidate /= part
        try:
            mode = candidate.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            return True
    return False
```

- [ ] **Step 5: Implement safe loading and sanitized parsing**

Add these imports and functions to `src/repo_doctor/config.py`; keep the Task 2 model
layer unchanged:

```python
import os
import stat
import tomllib

from pydantic import ValidationError

from repo_doctor.checks.filesystem import is_protected_path
from repo_doctor.path_safety import has_symlink_component, normalize_local_path


def _format_validation_error(error: ValidationError) -> str:
    first = error.errors(include_input=False, include_url=False)[0]
    location = ".".join(str(part) for part in first["loc"]) or "configuration"
    message = str(first.get("msg", "invalid value"))
    return f"{location}: {message}"


def _read_bounded_config(path: Path) -> bytes:
    if is_protected_path(path):
        raise ConfigError(f"refusing to read protected configuration path: {path}")
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
        candidate = normalize_local_path(explicit_paths[0], expand_user=True)
        return LoadedConfiguration(_load_config_file(candidate), candidate)

    candidate = repo_root / CONFIG_FILENAME
    try:
        candidate.lstat()
    except FileNotFoundError:
        return LoadedConfiguration(DEFAULT_CONFIG, None)
    except OSError as error:
        raise ConfigError(f"configuration file cannot be accessed: {candidate}") from error
    return LoadedConfiguration(_load_config_file(candidate), candidate)
```

Keep the preliminary `lstat` in automatic discovery: it distinguishes absence from
broken links. Do not replace it with `exists()` or `resolve()`.

- [ ] **Step 6: Run config tests and full unit regression**

Run: `uv run pytest tests/unit/test_config_models.py tests/unit/test_config_loading.py -v`

Expected: all configuration tests pass, including safety and non-leak assertions.

Run: `make test`

Expected: all unit tests pass with the existing Phase 0 count plus the new tests.

- [ ] **Step 7: Commit safe loading**

```bash
git add src/repo_doctor/config.py src/repo_doctor/path_safety.py tests/unit/test_config_loading.py
git commit -m "feat: add safe repository configuration loading"
```

## Task 4: Inject configured checks, scoring, and content exclusions

**Files:**

- Modify: `src/repo_doctor/scoring.py:1-17`
- Modify: `src/repo_doctor/scanner.py:1-49`
- Modify: `src/repo_doctor/checks/filesystem.py:1-69`
- Modify: `src/repo_doctor/checks/readme.py:23-31`
- Modify: `src/repo_doctor/checks/license.py:21-31`
- Modify: `src/repo_doctor/checks/tests.py:21-31`
- Modify: `src/repo_doctor/checks/env_example.py:57-123`
- Modify: `tests/unit/test_scoring.py:1-100`
- Modify: `tests/unit/test_scanner.py:1-45`
- Modify: `tests/unit/test_filesystem.py:1-20`
- Modify: `tests/unit/test_env_example_check.py:1-45`
- Modify: `tests/unit/test_config_models.py`

- [ ] **Step 1: Write failing scoring and selection tests**

Extend `tests/unit/test_scoring.py`, first adding `DEDUCTIONS` to its existing
scoring imports:

```python
from repo_doctor.scoring import (
    DEDUCTIONS,
    MAX_SCORE,
    calculate_score,
    summarize_score,
)


def test_custom_severity_deductions_are_applied() -> None:
    deductions = {
        Severity.HIGH: 3,
        Severity.MEDIUM: 2,
        Severity.LOW: 1,
        Severity.INFO: 0,
    }
    findings = [finding(Severity.HIGH), finding(Severity.MEDIUM), finding(Severity.LOW)]
    assert calculate_score(findings, deductions=deductions) == 94


def test_custom_zero_deduction_and_passed_findings_do_not_lower_score() -> None:
    deductions = dict(DEDUCTIONS)
    deductions[Severity.HIGH] = 0
    assert calculate_score(
        [finding(Severity.HIGH), finding(Severity.MEDIUM, passed=True)],
        deductions=deductions,
    ) == MAX_SCORE
```

Extend `tests/unit/test_config_models.py`:

```python
def test_check_selection_preserves_registry_order() -> None:
    config = RepoDoctorConfig.model_validate(
        {
            "version": 1,
            "checks": {
                "readme-sections": {"enabled": False},
                "docker-exists": {"enabled": False},
            },
        }
    )
    assert [check.id for check in select_checks(config)] == [
        "readme-exists",
        "license-exists",
        "tests-exist",
        "ci-exists",
        "env-example",
    ]
```

- [ ] **Step 2: Write failing scanner and exclusion tests**

Extend `tests/unit/test_scanner.py`, adding these imports beside its current scanner
imports:

```python
from repo_doctor.checks import DEFAULT_CHECKS
from repo_doctor.models import Severity


def test_scanner_accepts_custom_deductions(tmp_path: Path) -> None:
    deductions = {
        Severity.HIGH: 3,
        Severity.MEDIUM: 2,
        Severity.LOW: 1,
        Severity.INFO: 0,
    }
    report = scan_repository(tmp_path, deductions=deductions)
    assert report.score == 87


def test_scanner_runs_only_injected_checks(tmp_path: Path) -> None:
    selected = tuple(
        check for check in DEFAULT_CHECKS if check.id in {"license-exists", "docker-exists"}
    )
    report = scan_repository(tmp_path, checks=selected)
    assert [finding.id for finding in report.findings] == [
        "license-exists",
        "docker-exists",
    ]
    assert report.score == 75
```

The empty-repository custom score is `87`: two high failures deduct 6, three medium
failures deduct 6, one low failure deducts 1, and the passing environment check
deducts nothing.

Extend `tests/unit/test_env_example_check.py`:

```python
def test_effective_policy_is_excluded_from_environment_detection(tmp_path: Path) -> None:
    policy = tmp_path / ".repo-doctor.toml"
    policy.write_text("version = 1\n# env_file: .env\n", encoding="utf-8")
    finding = EnvExampleCheck().run(tmp_path, excluded_paths=frozenset({policy}))
    assert finding.passed is True


def test_other_toml_environment_signal_still_requires_example(tmp_path: Path) -> None:
    (tmp_path / "application.toml").write_text("# ${APP_TOKEN}\n", encoding="utf-8")
    finding = EnvExampleCheck().run(tmp_path, excluded_paths=frozenset())
    assert finding.passed is False
```

Extend `tests/unit/test_filesystem.py` to prove exclusions happen before candidate
metadata:

```python
def test_repository_traversal_skips_excluded_path_before_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = tmp_path / ".repo-doctor.toml"
    policy.write_text("version = 1\n", encoding="utf-8")
    original_is_symlink = Path.is_symlink

    def guarded_is_symlink(path: Path) -> bool:
        if path == policy:
            raise AssertionError("excluded policy metadata was inspected")
        return original_is_symlink(path)

    monkeypatch.setattr(Path, "is_symlink", guarded_is_symlink)
    files = tuple(
        iter_repository_files(
            tmp_path,
            excluded_paths=frozenset({policy}),
        )
    )
    assert policy not in files
```

Add `import pytest` and import `iter_repository_files` in that test module.

- [ ] **Step 3: Run focused tests and verify red state**

Run: `uv run pytest tests/unit/test_scoring.py tests/unit/test_scanner.py tests/unit/test_filesystem.py tests/unit/test_env_example_check.py tests/unit/test_config_models.py -v`

Expected: failures report unsupported `deductions`/`excluded_paths` behavior and the
policy file incorrectly influences environment detection.

- [ ] **Step 4: Make deductions injectable and immutable**

Replace the default mapping and score function in `src/repo_doctor/scoring.py`:

```python
from collections.abc import Mapping, Sequence
from types import MappingProxyType

from repo_doctor.models import Finding, Severity

MAX_SCORE = 100
DEDUCTIONS: Mapping[Severity, int] = MappingProxyType(
    {
        Severity.INFO: 0,
        Severity.LOW: 5,
        Severity.MEDIUM: 10,
        Severity.HIGH: 20,
    }
)


def calculate_score(
    findings: Sequence[Finding],
    *,
    deductions: Mapping[Severity, int] = DEDUCTIONS,
) -> int:
    deduction = sum(deductions[item.severity] for item in findings if not item.passed)
    return max(0, MAX_SCORE - deduction)
```

Keep `summarize_score` unchanged.

- [ ] **Step 5: Extract repository validation and inject scanner policy**

Refactor `src/repo_doctor/scanner.py` so its public functions have these exact
signatures and flow:

```python
from collections.abc import Collection, Mapping, Sequence

from repo_doctor.models import Report, Severity
from repo_doctor.scoring import DEDUCTIONS, MAX_SCORE, calculate_score, summarize_score


def resolve_repository_path(repo_path: Path) -> Path:
    try:
        resolved = repo_path.expanduser().resolve(strict=True)
    except FileNotFoundError as error:
        raise RepositoryScanError(f"Repository path does not exist: {repo_path}") from error
    except (OSError, RuntimeError) as error:
        raise RepositoryScanError(f"Repository path cannot be accessed: {repo_path}") from error
    if not resolved.is_dir():
        raise RepositoryScanError(f"Repository path is not a directory: {repo_path}")
    try:
        with os.scandir(resolved):
            pass
    except OSError as error:
        raise RepositoryScanError(f"Repository path is not readable: {repo_path}") from error
    return resolved


def scan_repository(
    repo_path: Path,
    *,
    checks: Sequence[Check] = DEFAULT_CHECKS,
    deductions: Mapping[Severity, int] = DEDUCTIONS,
    excluded_paths: Collection[Path] = (),
    generated_at: datetime | None = None,
) -> Report:
    resolved = resolve_repository_path(repo_path)
    exclusions = frozenset(excluded_paths)
    try:
        findings = tuple(
            check.run(resolved, excluded_paths=exclusions) for check in checks
        )
    except OSError as error:
        raise RepositoryScanError(
            f"Repository could not be read completely: {repo_path}"
        ) from error
    score = calculate_score(findings, deductions=deductions)
    return Report(
        repo_path=str(resolved),
        score=score,
        max_score=MAX_SCORE,
        summary=summarize_score(score),
        findings=findings,
        generated_at=generated_at or datetime.now(UTC),
        version=__version__,
    )
```

- [ ] **Step 6: Exclude policy paths before file metadata or content access**

Change `iter_repository_files` in `checks/filesystem.py` so an excluded file is
discarded before `is_symlink()` or any downstream metadata call:

```python
def iter_repository_files(
    repo_path: Path,
    *,
    excluded_paths: frozenset[Path] = frozenset(),
) -> Iterator[Path]:
    for directory, dir_names, file_names in repo_path.walk(
        top_down=True,
        follow_symlinks=False,
    ):
        dir_names[:] = sorted(
            name
            for name in dir_names
            if name not in EXCLUDED_DIRECTORIES
            and not _is_protected_name(name)
            and not (directory / name).is_symlink()
        )
        for name in sorted(file_names):
            candidate = directory / name
            if candidate in excluded_paths:
                continue
            if not _is_protected_name(name) and not candidate.is_symlink():
                yield candidate
```

In `find_readme`, put the name filter before metadata:

```python
entries = sorted(
    (
        entry
        for entry in repo_path.iterdir()
        if entry.name.casefold() in README_PRIORITY
        and not entry.is_symlink()
        and entry.is_file()
    ),
    key=lambda entry: entry.name,
)
```

In `LicenseCheck.run`, reorder the generator condition exactly:

```python
passed = any(
    entry.name.casefold() in LICENSE_NAMES
    and not entry.is_symlink()
    and entry.is_file()
    for entry in repo_path.iterdir()
)
```

In `TestsCheck.run`, pass the protocol exclusion into traversal:

```python
for path in iter_repository_files(
    repo_path,
    excluded_paths=excluded_paths,
)
```

Change the environment iterator and its call site:

```python
def _iter_candidate_files(
    repo_path: Path,
    *,
    excluded_paths: frozenset[Path] = frozenset(),
) -> Iterator[Path]:
    return iter_repository_files(repo_path, excluded_paths=excluded_paths)


usage_detected = any(
    _path_has_env_usage(path, readme, repo_path)
    for path in _iter_candidate_files(
        repo_path,
        excluded_paths=excluded_paths,
    )
)
```

Update the protected-environment spy in `test_env_example_check.py` to accept the
new keyword without reading either protected path:

```python
monkeypatch.setattr(
    env_module,
    "_iter_candidate_files",
    lambda _repo, *, excluded_paths=frozenset(): iter(protected),
)
```

- [ ] **Step 7: Run focused and full tests**

Run: `uv run pytest tests/unit/test_scoring.py tests/unit/test_scanner.py tests/unit/test_filesystem.py tests/unit/test_env_example_check.py tests/unit/test_config_models.py -v`

Expected: all focused tests pass.

Run: `make test`

Expected: the complete unit suite passes.

- [ ] **Step 8: Commit configurable scanning**

```bash
git add src/repo_doctor/scoring.py src/repo_doctor/scanner.py src/repo_doctor/checks/filesystem.py src/repo_doctor/checks/readme.py src/repo_doctor/checks/license.py src/repo_doctor/checks/tests.py src/repo_doctor/checks/env_example.py tests/unit/test_scoring.py tests/unit/test_scanner.py tests/unit/test_filesystem.py tests/unit/test_env_example_check.py tests/unit/test_config_models.py
git commit -m "feat: apply configured checks and scoring"
```

## Task 5: Integrate discovery and override behavior into the CLI

**Files:**

- Modify: `src/repo_doctor/cli.py:1-139`
- Modify: `tests/unit/test_cli.py:1-260`
- Modify: `tests/e2e/test_scan_fixtures.py:1-33`

- [ ] **Step 1: Add failing discovery, precedence, and configured-output tests**

Extend `tests/unit/test_cli.py` with a helper and these core cases:

```python
def write_policy(path: Path, body: str = "") -> None:
    path.write_text(f"version = 1\n{body}", encoding="utf-8")


def test_automatic_config_changes_json_findings_and_score(tmp_path: Path) -> None:
    write_policy(
        tmp_path / ".repo-doctor.toml",
        "[checks.readme-exists]\nenabled = false\n"
        "[checks.license-exists]\nenabled = false\n",
    )
    result = runner.invoke(app, ["scan", str(tmp_path), "--format", "json"])
    payload = json.loads(result.stdout)
    assert result.exit_code == 0
    assert payload["score"] == 65
    assert [finding["id"] for finding in payload["findings"]] == [
        "readme-sections",
        "tests-exist",
        "ci-exists",
        "docker-exists",
        "env-example",
    ]


def test_explicit_config_overrides_invalid_automatic_config(tmp_path: Path) -> None:
    (tmp_path / ".repo-doctor.toml").write_text("not valid toml = [", encoding="utf-8")
    explicit = tmp_path / "policy.toml"
    write_policy(explicit)
    result = runner.invoke(app, ["scan", str(tmp_path), "--config", str(explicit)])
    assert result.exit_code == 0


def test_explicit_config_prevents_root_policy_file_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    automatic = tmp_path / ".repo-doctor.toml"
    automatic.write_text("# env_file: .env\n", encoding="utf-8")
    explicit = tmp_path / "policy.toml"
    write_policy(explicit)
    original_lstat = Path.lstat
    original_stat = Path.stat
    original_read_text = Path.read_text

    def guarded_lstat(path: Path, *args: object, **kwargs: object):
        if path == automatic:
            raise AssertionError("automatic policy metadata was inspected")
        return original_lstat(path, *args, **kwargs)

    def guarded_stat(path: Path, *args: object, **kwargs: object):
        if path == automatic:
            raise AssertionError("automatic policy metadata was inspected")
        return original_stat(path, *args, **kwargs)

    def guarded_read_text(path: Path, *args: object, **kwargs: object) -> str:
        if path == automatic:
            raise AssertionError("automatic policy content was read")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", guarded_lstat)
    monkeypatch.setattr(Path, "stat", guarded_stat)
    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    result = runner.invoke(
        app,
        ["scan", str(tmp_path), "--config", str(explicit)],
    )
    assert result.exit_code == 0


def test_duplicate_config_option_exits_two(tmp_path: Path) -> None:
    policy = tmp_path / "policy.toml"
    write_policy(policy)
    result = runner.invoke(
        app,
        ["scan", str(tmp_path), "--config", str(policy), "--config", str(policy)],
    )
    assert result.exit_code == 2
    assert "only once" in result.stderr


def test_configured_score_drives_threshold_without_polluting_json(tmp_path: Path) -> None:
    write_policy(
        tmp_path / ".repo-doctor.toml",
        "[scoring]\nhigh = 3\nmedium = 2\nlow = 1\ninfo = 0\n",
    )
    result = runner.invoke(
        app,
        ["scan", str(tmp_path), "--format", "json", "--fail-under", "90"],
    )
    payload = json.loads(result.stdout)
    assert result.exit_code == 1
    assert payload["score"] == 87
    assert "Score 87" in result.stderr
```

Add these CLI contract tests:

```python
def test_missing_explicit_config_exits_two(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["scan", str(tmp_path), "--config", str(tmp_path / "missing.toml")],
    )
    assert result.exit_code == 2
    assert "does not exist" in result.stderr


def test_configured_terminal_count_uses_enabled_checks(tmp_path: Path) -> None:
    write_policy(
        tmp_path / ".repo-doctor.toml",
        "[checks.readme-exists]\nenabled = false\n"
        "[checks.license-exists]\nenabled = false\n",
    )
    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 0
    assert "1/5 checks passed" in result.stdout


def test_configured_json_keeps_report_shape(tmp_path: Path) -> None:
    write_policy(
        tmp_path / ".repo-doctor.toml",
        "[checks.docker-exists]\nenabled = false\n",
    )
    result = runner.invoke(app, ["scan", str(tmp_path), "--format", "json"])
    payload = json.loads(result.stdout)
    assert list(payload) == [
        "repo_path",
        "score",
        "max_score",
        "summary",
        "findings",
        "generated_at",
        "version",
    ]
    assert "configuration" not in payload


def test_scan_help_lists_config_option() -> None:
    result = runner.invoke(app, ["scan", "--help"])
    assert result.exit_code == 0
    assert "--config" in result.stdout
```

Extend `tests/e2e/test_scan_fixtures.py` with the cross-layer configured behavior
before implementing the CLI integration:

```python
def test_configured_repository_uses_discovery_and_custom_scoring(tmp_path: Path) -> None:
    policy = tmp_path / ".repo-doctor.toml"
    policy.write_text(
        "version = 1\n"
        "[scoring]\nhigh = 30\nmedium = 10\nlow = 5\ninfo = 0\n"
        "[checks.docker-exists]\nenabled = false\n",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["scan", str(tmp_path), "--format", "json"])
    payload = json.loads(result.stdout)
    assert result.exit_code == 0
    assert payload["score"] == 10
    assert [finding["id"] for finding in payload["findings"]] == [
        "readme-exists",
        "readme-sections",
        "license-exists",
        "tests-exist",
        "ci-exists",
        "env-example",
    ]
    assert list(payload) == [
        "repo_path",
        "score",
        "max_score",
        "summary",
        "findings",
        "generated_at",
        "version",
    ]
```

The configured score is `10`: two high failures deduct 60, three medium failures
deduct 30, the environment check passes, and Docker is disabled.

- [ ] **Step 2: Add failing sanitized-error and output-collision tests**

Add these representative safety cases:

```python
def test_invalid_config_value_is_not_echoed(tmp_path: Path) -> None:
    sentinel = "CLI_CONFIG_SENTINEL_MUST_NOT_LEAK"
    policy = tmp_path / ".repo-doctor.toml"
    policy.write_text(
        f'version = 1\n[scoring]\nhigh = "{sentinel}"\n',
        encoding="utf-8",
    )
    result = runner.invoke(app, ["scan", str(tmp_path), "--format", "json"])
    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr.startswith("Error: ")
    assert sentinel not in result.stderr
    assert "Traceback" not in result.stderr


def test_absent_root_policy_is_reserved_as_output(tmp_path: Path) -> None:
    policy = tmp_path / ".repo-doctor.toml"
    result = runner.invoke(
        app,
        ["scan", str(tmp_path), "--format", "json", "--output", str(policy)],
    )
    assert result.exit_code == 2
    assert policy.exists() is False


def test_effective_explicit_policy_cannot_be_output_target(tmp_path: Path) -> None:
    policy = tmp_path / "policy.toml"
    original = "version = 1\n"
    policy.write_text(original, encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "scan",
            str(tmp_path),
            "--config",
            str(policy),
            "--format",
            "markdown",
            "--output",
            str(policy),
        ],
    )
    assert result.exit_code == 2
    assert policy.read_text(encoding="utf-8") == original
```

Add every remaining collision case explicitly:

```python
def test_discovered_policy_cannot_be_output_target(tmp_path: Path) -> None:
    policy = tmp_path / ".repo-doctor.toml"
    original = "version = 1\n"
    policy.write_text(original, encoding="utf-8")
    result = runner.invoke(
        app,
        ["scan", str(tmp_path), "--format", "json", "--output", str(policy)],
    )
    assert result.exit_code == 2
    assert policy.read_text(encoding="utf-8") == original


def test_external_policy_does_not_unreserve_root_output(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    explicit = tmp_path / "external-policy.toml"
    write_policy(explicit)
    reserved = repo / ".repo-doctor.toml"
    result = runner.invoke(
        app,
        [
            "scan",
            str(repo),
            "--config",
            str(explicit),
            "--format",
            "json",
            "--output",
            str(reserved),
        ],
    )
    assert result.exit_code == 2
    assert reserved.exists() is False


def test_normalized_root_policy_alias_is_reserved(tmp_path: Path) -> None:
    output = tmp_path / "sub" / ".." / ".repo-doctor.toml"
    result = runner.invoke(
        app,
        ["scan", str(tmp_path), "--format", "json", "--output", str(output)],
    )
    assert result.exit_code == 2
    assert (tmp_path / ".repo-doctor.toml").exists() is False


def test_hard_link_alias_of_active_policy_is_rejected(tmp_path: Path) -> None:
    policy = tmp_path / "policy.toml"
    alias = tmp_path / "report.md"
    original = "version = 1\n"
    policy.write_text(original, encoding="utf-8")
    os.link(policy, alias)
    result = runner.invoke(
        app,
        [
            "scan",
            str(tmp_path),
            "--config",
            str(policy),
            "--format",
            "markdown",
            "--output",
            str(alias),
        ],
    )
    assert result.exit_code == 2
    assert policy.read_text(encoding="utf-8") == original
```

Keep every existing protected-path, symlink, FIFO, normal JSON/Markdown write,
threshold-order, and I/O-failure test.

Add this parameterized invalid-policy contract:

```python
ALL_DISABLED_POLICY = (
    "version = 1\n"
    "[checks.readme-exists]\nenabled = false\n"
    "[checks.readme-sections]\nenabled = false\n"
    "[checks.license-exists]\nenabled = false\n"
    "[checks.tests-exist]\nenabled = false\n"
    "[checks.ci-exists]\nenabled = false\n"
    "[checks.docker-exists]\nenabled = false\n"
    "[checks.env-example]\nenabled = false\n"
).encode()


@pytest.mark.parametrize(
    "payload",
    [
        b"version = [",
        b"version = 2\n",
        b"version = 1\n[checks.unknown-check]\nenabled = true\n",
        b"version = 1\n[scoring]\nhigh = 9\nmedium = 10\n",
        ALL_DISABLED_POLICY,
        b"\xff",
    ],
)
def test_invalid_automatic_config_has_clean_error(
    tmp_path: Path, payload: bytes
) -> None:
    policy = tmp_path / ".repo-doctor.toml"
    output = tmp_path / "report.json"
    policy.write_bytes(payload)
    result = runner.invoke(
        app,
        [
            "scan",
            str(tmp_path),
            "--format",
            "json",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr.startswith("Error: ")
    assert "Traceback" not in result.stderr
    assert output.exists() is False


def test_oversized_automatic_config_has_clean_error(tmp_path: Path) -> None:
    policy = tmp_path / ".repo-doctor.toml"
    output = tmp_path / "report.json"
    policy.write_bytes(b"version = 1\n#" + (b"x" * (1024 * 1024)))
    result = runner.invoke(
        app,
        [
            "scan",
            str(tmp_path),
            "--format",
            "json",
            "--output",
            str(output),
        ],
    )
    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr.startswith("Error: ")
    assert output.exists() is False
```

- [ ] **Step 3: Run CLI tests and verify red state**

Run: `uv run pytest tests/unit/test_cli.py tests/e2e/test_scan_fixtures.py::test_configured_repository_uses_discovery_and_custom_scoring -v`

Expected: unit and end-to-end tests fail because `--config`, selection, and
collision protection are not wired into the CLI.

- [ ] **Step 4: Reuse shared path helpers and add collision detection**

Remove `_normalize_output_path` and `_has_symlink_component` from `cli.py`. Import
`normalize_local_path` and `has_symlink_component` from `repo_doctor.path_safety`.
Keep `_is_protected_output` unchanged.

Add these helpers, using lexical comparison for the reserved root so an explicit
policy never metadata-probes an unused automatic file:

```python
def _same_existing_file(first: Path, second: Path) -> bool:
    if first == second:
        return True
    try:
        return os.path.samefile(first, second)
    except (FileNotFoundError, OSError):
        return False


def _validate_output_path(
    path: Path,
    *,
    reserved_root_policy: Path,
    active_policy: Path | None,
) -> None:
    if _is_protected_output(path):
        raise ValueError("refusing to write a report to a protected secret path")
    if has_symlink_component(path):
        raise ValueError("refusing to write a report through a symbolic link")
    if path == reserved_root_policy:
        raise ValueError("refusing to overwrite the repository configuration path")
    if active_policy is not None and _same_existing_file(path, active_policy):
        raise ValueError("refusing to overwrite the active configuration file")

    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return
    if not stat.S_ISREG(mode):
        raise ValueError("refusing to replace a non-regular output target")


def _write_report(
    path: Path,
    content: str,
    *,
    reserved_root_policy: Path,
    active_policy: Path | None,
) -> None:
    _validate_output_path(
        path,
        reserved_root_policy=reserved_root_policy,
        active_policy=active_policy,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    _validate_output_path(
        path,
        reserved_root_policy=reserved_root_policy,
        active_policy=active_policy,
    )
    path.write_text(content, encoding="utf-8")
```

- [ ] **Step 5: Add `--config` and orchestrate the effective policy**

Import `CONFIG_FILENAME`, `ConfigError`, `resolve_configuration`, `select_checks`,
and `severity_deductions`. Import `resolve_repository_path` from the scanner.

Add the Typer option as a repeat-capturing list:

```python
config: Annotated[
    list[Path] | None,
    typer.Option(
        "--config",
        help="Use this TOML policy instead of repository-root discovery.",
    ),
] = None,
```

Use this orchestration inside `scan`, before rendering:

```python
if output is not None and output_format is OutputFormat.TERMINAL:
    _exit_error("--output requires JSON or Markdown format")

try:
    resolved_repo = resolve_repository_path(path)
    loaded = resolve_configuration(
        resolved_repo,
        explicit_paths=tuple(config or ()),
    )
except (ConfigError, RepositoryScanError) as error:
    _exit_error(str(error))

reserved_root_policy = resolved_repo / CONFIG_FILENAME
if output is not None:
    output = normalize_local_path(output)
    try:
        _validate_output_path(
            output,
            reserved_root_policy=reserved_root_policy,
            active_policy=loaded.source_path,
        )
    except (OSError, ValueError) as error:
        _exit_error(str(error))

selected_checks = select_checks(loaded.settings)
exclusions = {reserved_root_policy}
if loaded.source_path is not None:
    exclusions.add(loaded.source_path)
try:
    report = scan_repository(
        resolved_repo,
        checks=selected_checks,
        deductions=severity_deductions(loaded.settings),
        excluded_paths=exclusions,
    )
except RepositoryScanError as error:
    _exit_error(str(error))
```

Pass `reserved_root_policy` and `loaded.source_path` into `_write_report`. Update the
existing scanner monkeypatch in `test_unreadable_repository_error_exits_two` to accept
`**kwargs: object`, because configured orchestration now uses keyword arguments.

- [ ] **Step 6: Run CLI tests and all unit tests**

Run: `uv run pytest tests/unit/test_cli.py -v`

Expected: all existing and new CLI tests pass.

Run: `make test`

Expected: the complete unit suite passes.

- [ ] **Step 7: Run static checks for the integration milestone**

Run: `uv run ruff check src tests/unit`

Expected: exit 0.

Run: `uv run mypy src`

Expected: exit 0 under strict mode.

- [ ] **Step 8: Commit CLI configuration support**

```bash
git add src/repo_doctor/cli.py tests/unit/test_cli.py tests/e2e/test_scan_fixtures.py
git commit -m "feat: add configurable scan policies"
```

## Task 6: Ship the canonical policy, Phase 1 version, and end-to-end proof

**Files:**

- Create: `.repo-doctor.toml`
- Modify: `src/repo_doctor/__init__.py:3`
- Modify: `pyproject.toml:7`
- Modify: `uv.lock:37-38`
- Modify: `tests/unit/conftest.py:9-38`
- Modify: `tests/unit/test_scanner.py`
- Modify: `tests/e2e/test_scan_fixtures.py:1-33`

- [ ] **Step 1: Strengthen default compatibility and root-policy assertions**

Update fixture assertions to exact values and add a root-policy parity test:

```python
PROJECT_ROOT = Path(__file__).parents[2]


def test_good_fixture_has_exact_default_report() -> None:
    report = scan_repository(FIXTURES / "good_repo")
    assert report.score == 100
    assert len(report.findings) == 7
    assert all(finding.passed for finding in report.findings)
    assert report.version == "0.2.0"


def test_bad_fixture_has_exact_default_report() -> None:
    report = scan_repository(FIXTURES / "bad_repo")
    assert report.score == 25
    assert len(report.findings) == 7
    assert report.version == "0.2.0"


def test_committed_root_policy_matches_builtin_defaults() -> None:
    policy = PROJECT_ROOT / ".repo-doctor.toml"
    assert policy.is_file()
    configured = runner.invoke(
        app,
        ["scan", str(PROJECT_ROOT), "--format", "json"],
    )
    default_report = scan_repository(PROJECT_ROOT)
    payload = json.loads(configured.stdout)
    assert configured.exit_code == 0
    assert payload["score"] == default_report.score == 85
    assert [finding["id"] for finding in payload["findings"]] == [
        finding.id for finding in default_report.findings
    ]
    assert payload["version"] == default_report.version == "0.2.0"
```

Add `assert report.version == "0.2.0"` to a scanner unit test. Update fixed report
fixtures that represent current package output from `0.1.0` to `0.2.0`.

- [ ] **Step 2: Run compatibility tests and verify red state**

Run: `uv run pytest tests/e2e/test_scan_fixtures.py tests/unit/test_scanner.py -v`

Expected: the root-policy test fails because the canonical file is not committed yet,
and version assertions fail at `0.1.0`.

- [ ] **Step 3: Add the canonical root policy**

Create `.repo-doctor.toml` exactly:

```toml
version = 1

[scoring]
high = 20
medium = 10
low = 5
info = 0

[checks.readme-exists]
enabled = true

[checks.readme-sections]
enabled = true

[checks.license-exists]
enabled = true

[checks.tests-exist]
enabled = true

[checks.ci-exists]
enabled = true

[checks.docker-exists]
enabled = true

[checks.env-example]
enabled = true
```

- [ ] **Step 4: Advance package and report version to 0.2.0**

Change `src/repo_doctor/__init__.py` to:

```python
"""GitHub Repo Doctor package."""

__version__ = "0.2.0"
```

Change `[project].version` in `pyproject.toml` to `0.2.0`, then run:

Run: `uv lock`

Expected: the root package entry in `uv.lock` changes to `version = "0.2.0"` with no
dependency additions or upgrades.

- [ ] **Step 5: Run unit and e2e tests**

Run: `make test`

Expected: all unit tests pass.

Run: `make test-e2e`

Expected: good fixture `100`, bad fixture `25`, configured repository `10`, and
root-policy parity at `85` all pass.

- [ ] **Step 6: Prove the committed policy matches built-ins**

Run: `uv run repo-doctor scan . --format json`

Expected: exit 0, score `85`, seven ordered findings with five passes, and version
`0.2.0`.

- [ ] **Step 7: Commit policy, version, and e2e coverage**

```bash
git add .repo-doctor.toml src/repo_doctor/__init__.py pyproject.toml uv.lock tests/unit/conftest.py tests/unit/test_scanner.py tests/e2e/test_scan_fixtures.py
git commit -m "feat: ship repository configuration policy"
```

## Task 7: Document configuration and contributor rules

**Files:**

- Modify: `README.md:1-171`
- Modify: `docs/SCORING.md:1-89`
- Modify: `docs/DECISIONS.md:1-71`
- Inspect and conditionally modify: `docs/FAILURES.md`
- Modify: `AGENTS.md:15-31`

- [ ] **Step 1: Update the README product and quickstart language**

Change “Phase 0 checks” in the opening to “Repo Doctor checks,” and add these commands
to Quickstart after the existing three:

```bash
repo-doctor scan . --config custom-doctor.toml
repo-doctor scan . --format markdown --output report.md
```

Add this section before “Example terminal report”:

````markdown
## Configuration

Repo Doctor automatically loads `.repo-doctor.toml` from the resolved repository
root. Use `--config FILE` to replace automatic discovery with one explicit policy.
Omitted scoring values and check tables inherit the built-in defaults.

```toml
version = 1

[scoring]
high = 20
medium = 10
low = 5
info = 0

[checks.docker-exists]
enabled = false
```

Checks can be configured by their finding IDs: `readme-exists`,
`readme-sections`, `license-exists`, `tests-exist`, `ci-exists`,
`docker-exists`, and `env-example`. Disabled checks do not run, appear in reports,
or deduct points. At least one check must remain enabled.

Only one policy is used. An explicit `--config` replaces repository discovery;
the two files are never merged. Invalid versions, keys, IDs, types, deductions, or
duplicate `--config` options exit 2 without printing policy values.
````

The four-backtick outer fence keeps the nested TOML fence valid in this plan.

- [ ] **Step 2: Update JSON, scoring, limitations, and roadmap statements**

Change the README JSON example version to `0.2.0`. Replace “all seven check results”
with:

```markdown
Passed and failed enabled checks remain in JSON in registry order. Configuration
metadata is not embedded, so preserve a custom policy alongside reports when an
auditable score calculation is required.
```

State that output cannot target the repository-root or active policy. Update the
Scoring section to mention configurable global deductions. Change Phase 0 limitation
language to “The local scanner,” and replace the configuration roadmap item with:

```markdown
- Add deterministic contribution, security-policy, and community-health checks.
```

- [ ] **Step 3: Expand the scoring contract**

Add this immediately after the default severity table in `docs/SCORING.md`:

```markdown
These are the built-in defaults. A version-1 `.repo-doctor.toml` may override all
four global deductions with integers from 0 through 100. `info` must remain zero,
and values must satisfy `high >= medium >= low >= info`. Scores still begin at 100
and clamp at zero.

Each check may be disabled independently under `[checks.<finding-id>]`. Disabled
checks are outside the effective policy: they do not run, appear in findings, or
deduct points. At least one check must remain enabled. Check order always follows
the built-in registry rather than TOML table order.
```

Change “Not checked in Phase 0” to “Not checked yet,” and document that the effective
policy source is excluded from environment-usage content detection.

- [ ] **Step 4: Record durable Phase 1 decisions**

Append these entries to `docs/DECISIONS.md`:

```markdown
## 2026-07-19 — Use one versioned TOML policy

Repo Doctor discovers `.repo-doctor.toml` at the resolved repository root. One
explicit `--config` replaces discovery instead of merging policies. Standard-library
`tomllib` and strict Pydantic models keep the contract deterministic without a new
runtime dependency.

## 2026-07-19 — Filter checks and inject global severity deductions

Checks expose unique stable IDs before execution. Disabled checks are omitted rather
than reported as passes, registry order remains authoritative, and configurable
deductions preserve severity ordering. Disabling every check is invalid.

## 2026-07-19 — Preserve the report shape and version semantic changes

Phase 1 keeps every Finding and Report field unchanged but allows the findings list
to contain only enabled checks. Version `0.2.0` signals that semantic change. Reports
do not embed policy metadata; users needing score reproducibility preserve the policy
beside the report.

## 2026-07-19 — Treat policy files as bounded inputs and protected outputs

Configuration loading rejects protected paths, symlinks, non-regular files,
oversized content, invalid UTF-8, and unsafe schema values before scanning. Error
translation omits input values. Report output cannot replace the active policy or
the reserved repository-root policy path.
```

- [ ] **Step 5: Update contributor guidance and failure records accurately**

Add these bullets under `AGENTS.md` “Engineering Rules”:

```markdown
- Keep `.repo-doctor.toml` schema changes versioned, strict, and backward-conscious.
- Derive configurable check IDs from the ordered check registry; never duplicate the
  registry in configuration code.
- Add default-compatibility, invalid-config, and secret-safety tests for every policy
  behavior change.
- Keep active policy contents out of environment-usage detection and report output.
```

Inspect `docs/FAILURES.md`. If all observed failures are repetitions of its existing
sandbox loopback or patch-helper entries, leave it byte-for-byte unchanged. If a new
failure occurred during Tasks 1–6, add one dated entry containing its exact symptom,
impact, resolution, and status; do not invent a failure for documentation symmetry.

- [ ] **Step 6: Verify documentation against real CLI help and output**

Run: `uv run repo-doctor scan --help`

Expected: help includes `--config`, `--format`, `--output`, and `--fail-under` with the
documented meanings.

Run: `uv run repo-doctor scan . --format json`

Expected: README field names and version match actual JSON; score is `85` under the
canonical root policy.

Run: `git diff --check`

Expected: exit 0.

- [ ] **Step 7: Commit documentation**

```bash
git add README.md docs/SCORING.md docs/DECISIONS.md AGENTS.md
git add docs/FAILURES.md
git commit -m "docs: document repository configuration"
```

Before the second `git add`, confirm `docs/FAILURES.md` contains no invented entry. If
it is unchanged, Git simply stages nothing for that path.

## Task 8: Run release acceptance and leave a clean repository

**Files:**

- Verify only; modify a file only to fix a failure found by these checks.

- [ ] **Step 1: Synchronize the environment**

Run: `make install`

Expected: uv resolves the existing dependency set and exits 0 without adding a new
runtime package.

- [ ] **Step 2: Run every automated quality gate**

Run each command separately:

```text
make test
make test-e2e
make lint
make typecheck
make build
```

Expected: every command exits 0; pytest has no failures, Ruff has no diagnostics,
mypy is strict-clean, and both source and wheel distributions build.

- [ ] **Step 3: Verify default and configured CLI behavior**

Run: `uv run repo-doctor scan .`

Expected: exit 0 with `85/100` and `5/7 checks passed`; the missing root CI and
Docker findings remain visible.

Run: `uv run repo-doctor scan tests/fixtures/good_repo --format json --output /tmp/repo-doctor-phase1-good.json`

Expected: exit 0 and a JSON report file.

Run: `uv run python -m json.tool /tmp/repo-doctor-phase1-good.json`

Expected: valid JSON containing score `100`, seven findings, and version `0.2.0`.

Run: `uv run repo-doctor scan tests/fixtures/bad_repo`

Expected: exit 0 with score `25`.

Run: `uv run repo-doctor scan tests/fixtures/bad_repo --fail-under 80`

Expected: report renders and the process exits exactly 1.

- [ ] **Step 4: Inspect distribution contents**

Run: `uv build`

Expected: source and wheel artifact paths are printed with no warning.

Run: `tar -tf dist/github_repo_doctor-0.2.0.tar.gz`

Expected: the source archive lists every module under `src/repo_doctor`, `py.typed`,
project metadata, and `LICENSE`.

Run: `unzip -l dist/github_repo_doctor-0.2.0-py3-none-any.whl`

Expected: the wheel lists every runtime module, `py.typed`, distribution metadata,
the entry-point file, and the MIT license.

Run: `unzip -p dist/github_repo_doctor-0.2.0-py3-none-any.whl github_repo_doctor-0.2.0.dist-info/METADATA`

Expected: metadata reports version `0.2.0` and runtime requirements only for
Pydantic, Rich, and Typer.

- [ ] **Step 5: Review changes and commit only genuine fixes**

Run: `git diff --check`

Expected: exit 0.

Run: `git status --short`

Expected: no output. If acceptance exposed a defect, write a regression test, make
the smallest fix, rerun the affected gate plus all five quality gates, and commit the
tested fix with an accurate conventional `fix:` message before continuing.

- [ ] **Step 6: Record final delivery evidence**

Run: `rm /tmp/repo-doctor-phase1-good.json`

Expected: the temporary validation report is removed; no repository file changes.

Run: `rg --files --hidden -g '!.git/**'`

Expected: the final file inventory includes `.repo-doctor.toml`, `config.py`,
`path_safety.py`, all test modules, and all required documentation.

Run: `git log --oneline --decorate -12`

Expected: the Phase 1 design and implementation milestones appear as separate
conventional commits.

Run: `git status --short`

Expected: no output. Do not push.
