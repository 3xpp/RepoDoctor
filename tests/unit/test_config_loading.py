from __future__ import annotations

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


def valid_policy_of_size(size: int) -> bytes:
    prefix = b"version = 1\n#"
    return prefix + (b"x" * (size - len(prefix) - 1)) + b"\n"


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

    def guarded_lstat(path: Path, *args: object, **kwargs: object) -> os.stat_result:
        if path == automatic:
            raise AssertionError("automatic candidate was inspected")
        return original_lstat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", guarded_lstat)

    loaded = resolve_configuration(tmp_path, explicit_paths=(explicit,))

    assert loaded.source_path == explicit


def test_duplicate_explicit_options_fail_before_file_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_lstat(*args: object, **kwargs: object) -> os.stat_result:
        raise AssertionError("duplicate paths triggered file access")

    monkeypatch.setattr(Path, "lstat", fail_lstat)

    with pytest.raises(ConfigError, match="only once"):
        resolve_configuration(
            tmp_path,
            explicit_paths=(tmp_path / "one.toml", tmp_path / "two.toml"),
        )


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


@pytest.mark.parametrize("error_type", [RuntimeError, OSError])
def test_explicit_path_normalization_failure_is_sanitized(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[Exception],
) -> None:
    requested = Path("~/policy.toml")
    sentinel = "RAW_PATH_ERROR_MUST_NOT_LEAK"

    def fail_expanduser(path: Path) -> Path:
        assert path == requested
        raise error_type(sentinel)

    monkeypatch.setattr(Path, "expanduser", fail_expanduser)

    with pytest.raises(ConfigError, match="path cannot be normalized") as captured:
        resolve_configuration(tmp_path, explicit_paths=(requested,))

    assert sentinel not in str(captured.value)


def test_explicit_path_is_normalized_lexically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    nested = tmp_path / "nested"
    nested.mkdir()
    policy = tmp_path / "policy.toml"
    policy.write_text("version = 1\n", encoding="utf-8")
    monkeypatch.chdir(nested)

    loaded = resolve_configuration(
        tmp_path,
        explicit_paths=(Path(".") / ".." / "policy.toml",),
    )

    assert loaded.source_path == policy


def test_missing_explicit_config_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="does not exist"):
        resolve_configuration(
            tmp_path,
            explicit_paths=(tmp_path / "missing-policy.toml",),
        )


@pytest.mark.parametrize("broken", [False, True])
def test_automatic_config_rejects_symlinked_repository_root(tmp_path: Path, broken: bool) -> None:
    real_root = tmp_path / ("missing-root" if broken else "real-root")
    if not broken:
        real_root.mkdir()
    linked_root = tmp_path / "linked-root"
    linked_root.symlink_to(real_root, target_is_directory=True)

    with pytest.raises(ConfigError, match="symbolic link"):
        resolve_configuration(linked_root)


def test_exact_size_limit_is_accepted(tmp_path: Path) -> None:
    policy = tmp_path / "policy.toml"
    payload = valid_policy_of_size(MAX_CONFIG_BYTES)
    assert len(payload) == MAX_CONFIG_BYTES
    policy.write_bytes(payload)

    loaded = resolve_configuration(tmp_path, explicit_paths=(policy,))

    assert loaded.settings.version == 1


def test_size_limit_plus_one_is_rejected(tmp_path: Path) -> None:
    policy = tmp_path / "policy.toml"
    policy.write_bytes(valid_policy_of_size(MAX_CONFIG_BYTES + 1))

    with pytest.raises(ConfigError, match="larger than 1 MiB"):
        resolve_configuration(tmp_path, explicit_paths=(policy,))


def test_protected_path_is_rejected_before_metadata_or_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    protected = tmp_path / "secrets.toml"

    def fail_lstat(*args: object, **kwargs: object) -> os.stat_result:
        raise AssertionError("protected path metadata was inspected")

    def fail_open(*args: object, **kwargs: object) -> int:
        raise AssertionError("protected path was opened")

    monkeypatch.setattr(Path, "lstat", fail_lstat)
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

    def recording_open(path: Path, flags: int, *args: object) -> int:
        nonlocal observed_flags
        observed_flags = flags
        return real_open(path, flags, *args)

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


@pytest.mark.parametrize(
    ("payload", "message"),
    [(b"\xff", "UTF-8"), (b"version = [", "invalid TOML")],
)
def test_invalid_text_is_rejected(tmp_path: Path, payload: bytes, message: str) -> None:
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

    def deny_target(path: Path, *args: object, **kwargs: object) -> os.stat_result:
        if path == policy:
            raise PermissionError("denied")
        return original_lstat(path, *args, **kwargs)

    monkeypatch.setattr(Path, "lstat", deny_target)

    with pytest.raises(ConfigError, match="cannot be accessed"):
        resolve_configuration(tmp_path, explicit_paths=(policy,))


def test_open_failure_is_translated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    policy = tmp_path / "policy.toml"
    policy.write_text("version = 1\n", encoding="utf-8")

    def deny_open(*args: object, **kwargs: object) -> int:
        raise PermissionError("denied")

    monkeypatch.setattr(config_module.os, "open", deny_open)

    with pytest.raises(ConfigError, match="could not be read"):
        resolve_configuration(tmp_path, explicit_paths=(policy,))


def test_fstat_failure_is_translated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    policy = tmp_path / "policy.toml"
    policy.write_text("version = 1\n", encoding="utf-8")

    def deny_fstat(descriptor: int) -> os.stat_result:
        raise PermissionError(f"descriptor {descriptor} denied")

    monkeypatch.setattr(config_module.os, "fstat", deny_fstat)

    with pytest.raises(ConfigError, match="could not be read"):
        resolve_configuration(tmp_path, explicit_paths=(policy,))


def test_opened_descriptor_must_be_regular(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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

    def stale_lstat(path: Path, *args: object, **kwargs: object) -> os.stat_result:
        result = original_lstat(path, *args, **kwargs)
        if path != policy:
            return result
        values = list(result)
        values[6] = MAX_CONFIG_BYTES
        return os.stat_result(values)

    monkeypatch.setattr(Path, "lstat", stale_lstat)

    with pytest.raises(ConfigError, match="larger than 1 MiB"):
        resolve_configuration(tmp_path, explicit_paths=(policy,))
