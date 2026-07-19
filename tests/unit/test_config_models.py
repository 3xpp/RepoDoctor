from collections.abc import Mapping
from pathlib import Path

import pytest
from pydantic import ValidationError

from repo_doctor.checks import DEFAULT_CHECK_IDS, DEFAULT_CHECKS
from repo_doctor.config import (
    CONFIG_FILENAME,
    CONFIG_VERSION,
    DEFAULT_CONFIG,
    MAX_CONFIG_BYTES,
    CheckSettings,
    LoadedConfiguration,
    RepoDoctorConfig,
    ScoringSettings,
    enabled_check_ids,
    select_checks,
    severity_deductions,
)
from repo_doctor.models import Severity


def test_builtin_configuration_matches_phase_zero() -> None:
    assert CONFIG_FILENAME == ".repo-doctor.toml"
    assert CONFIG_VERSION == 1
    assert MAX_CONFIG_BYTES == 1024 * 1024
    assert DEFAULT_CONFIG.version == CONFIG_VERSION
    assert enabled_check_ids(DEFAULT_CONFIG) == DEFAULT_CHECK_IDS
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
    checks = {check_id: {"enabled": True} for check_id in enabled_check_ids(DEFAULT_CONFIG)}
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
    checks = {check_id: {"enabled": False} for check_id in enabled_check_ids(DEFAULT_CONFIG)}
    with pytest.raises(ValidationError, match="at least one check"):
        RepoDoctorConfig.model_validate({"version": 1, "checks": checks})


def test_configuration_models_and_mappings_are_read_only() -> None:
    config = RepoDoctorConfig.model_validate(
        {"version": 1, "checks": {"docker-exists": {"enabled": False}}}
    )
    assert isinstance(config.checks, Mapping)
    with pytest.raises(TypeError):
        config.checks["docker-exists"] = CheckSettings(enabled=True)  # type: ignore[index]
    with pytest.raises(ValidationError):
        config.version = 1
    with pytest.raises(ValidationError):
        config.scoring.high = 30


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


def test_enabled_ids_and_selected_checks_keep_registry_order() -> None:
    config = RepoDoctorConfig.model_validate(
        {
            "version": 1,
            "checks": {
                "docker-exists": {"enabled": False},
                "readme-exists": {"enabled": False},
            },
        }
    )
    expected_ids = tuple(
        check_id
        for check_id in DEFAULT_CHECK_IDS
        if check_id not in {"readme-exists", "docker-exists"}
    )
    assert enabled_check_ids(config) == expected_ids
    assert tuple(check.id for check in select_checks(config)) == expected_ids
    assert select_checks(config) == tuple(
        check for check in DEFAULT_CHECKS if check.id in expected_ids
    )


def test_severity_deductions_mapping_is_read_only_and_isolated() -> None:
    config = RepoDoctorConfig.model_validate({"version": 1, "scoring": {"high": 30}})
    deductions = severity_deductions(config)
    with pytest.raises(TypeError):
        deductions[Severity.HIGH] = 40  # type: ignore[index]
    assert deductions[Severity.HIGH] == 30
    assert severity_deductions(DEFAULT_CONFIG)[Severity.HIGH] == 20


def test_loaded_configuration_tracks_settings_and_optional_source() -> None:
    source_path = Path("policy.toml")
    loaded = LoadedConfiguration(settings=DEFAULT_CONFIG, source_path=source_path)
    assert loaded.settings is DEFAULT_CONFIG
    assert loaded.source_path == source_path
    with pytest.raises(AttributeError):
        loaded.source_path = None
