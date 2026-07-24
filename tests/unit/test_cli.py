import json
import os
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

import repo_doctor.cli as cli_module
from repo_doctor.cli import app
from repo_doctor.scanner import RepositoryScanError

runner = CliRunner()
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def write_policy(path: Path, body: str = "") -> None:
    path.write_text(f"version = 1\n{body}", encoding="utf-8")


def test_json_scan_writes_machine_only_stdout(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("print('hello')\n", encoding="utf-8")
    result = runner.invoke(app, ["scan", str(tmp_path), "--format", "json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["score"] == 25


def test_low_score_only_fails_with_threshold(tmp_path: Path) -> None:
    normal = runner.invoke(app, ["scan", str(tmp_path)])
    threshold = runner.invoke(app, ["scan", str(tmp_path), "--fail-under", "80"])
    assert normal.exit_code == 0
    assert threshold.exit_code == 1


def test_json_output_file_is_written(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    output = tmp_path / "reports" / "report.json"
    result = runner.invoke(
        app,
        ["scan", str(repo), "--format", "json", "--output", str(output)],
    )
    assert result.exit_code == 0
    assert json.loads(output.read_text(encoding="utf-8"))["score"] == 25


def test_protected_output_path_is_refused_without_touching_it(tmp_path: Path) -> None:
    protected = tmp_path / ".env"
    result = runner.invoke(
        app,
        ["scan", str(tmp_path), "--format", "json", "--output", str(protected)],
    )
    assert result.exit_code == 2
    assert protected.exists() is False


def test_output_target_symlink_is_refused_without_touching_target(tmp_path: Path) -> None:
    target = tmp_path / "existing-report.json"
    target.write_text("unchanged\n", encoding="utf-8")
    output = tmp_path / "report.json"
    output.symlink_to(target)

    result = runner.invoke(
        app,
        ["scan", str(tmp_path), "--format", "json", "--output", str(output)],
    )

    assert result.exit_code == 2
    assert target.read_text(encoding="utf-8") == "unchanged\n"
    assert output.is_symlink()


def test_broken_output_target_symlink_is_refused(tmp_path: Path) -> None:
    target = tmp_path / "missing-report.json"
    output = tmp_path / "report.json"
    output.symlink_to(target)

    result = runner.invoke(
        app,
        ["scan", str(tmp_path), "--format", "json", "--output", str(output)],
    )

    assert result.exit_code == 2
    assert target.exists() is False
    assert output.is_symlink()


def test_output_parent_symlink_is_refused_without_touching_target(tmp_path: Path) -> None:
    real_parent = tmp_path / "real-reports"
    real_parent.mkdir()
    target = real_parent / "report.json"
    target.write_text("unchanged\n", encoding="utf-8")
    output_parent = tmp_path / "reports"
    output_parent.symlink_to(real_parent, target_is_directory=True)

    result = runner.invoke(
        app,
        [
            "scan",
            str(tmp_path),
            "--format",
            "json",
            "--output",
            str(output_parent / "report.json"),
        ],
    )

    assert result.exit_code == 2
    assert target.read_text(encoding="utf-8") == "unchanged\n"
    assert output_parent.is_symlink()


def test_broken_output_parent_symlink_is_refused(tmp_path: Path) -> None:
    target_parent = tmp_path / "missing-reports"
    output_parent = tmp_path / "reports"
    output_parent.symlink_to(target_parent, target_is_directory=True)

    result = runner.invoke(
        app,
        [
            "scan",
            str(tmp_path),
            "--format",
            "json",
            "--output",
            str(output_parent / "report.json"),
        ],
    )

    assert result.exit_code == 2
    assert target_parent.exists() is False
    assert output_parent.is_symlink()


def test_normalized_output_refuses_symlink_before_creating_directories(tmp_path: Path) -> None:
    target_parent = tmp_path / "real-reports"
    target_parent.mkdir()
    output_parent = tmp_path / "reports"
    output_parent.symlink_to(target_parent, target_is_directory=True)
    output = tmp_path / "missing" / ".." / "reports" / "new" / "report.json"

    result = runner.invoke(
        app,
        ["scan", str(tmp_path), "--format", "json", "--output", str(output)],
    )

    assert result.exit_code == 2
    assert (tmp_path / "missing").exists() is False
    assert (target_parent / "new").exists() is False


def test_relative_output_from_protected_named_cwd_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    protected_named_cwd = tmp_path / "credentials"
    protected_named_cwd.mkdir()
    monkeypatch.chdir(protected_named_cwd)

    result = runner.invoke(
        app,
        ["scan", str(tmp_path), "--format", "json", "--output", "report.json"],
    )

    assert result.exit_code == 2
    assert (protected_named_cwd / "report.json").exists() is False


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO files are not supported")
def test_fifo_output_target_is_refused_without_opening_it(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    output = tmp_path / "report.json"
    os.mkfifo(output)

    result = runner.invoke(
        app,
        ["scan", str(repo), "--format", "json", "--output", str(output)],
    )

    assert result.exit_code == 2
    assert output.exists()
    assert output.stat().st_size == 0


def test_markdown_output_file_is_written(tmp_path: Path) -> None:
    output = tmp_path / "report.md"
    result = runner.invoke(
        app,
        ["scan", str(tmp_path), "--format", "markdown", "--output", str(output)],
    )
    assert result.exit_code == 0
    assert output.read_text(encoding="utf-8").startswith("# GitHub Repo Doctor Report")


def test_terminal_output_file_is_rejected(tmp_path: Path) -> None:
    result = runner.invoke(app, ["scan", str(tmp_path), "--output", "report.txt"])
    assert result.exit_code == 2


def test_missing_repository_exits_two(tmp_path: Path) -> None:
    result = runner.invoke(app, ["scan", str(tmp_path / "missing")])
    assert result.exit_code == 2


@pytest.mark.parametrize("value", ["-1", "101"])
def test_threshold_bounds_exit_two(tmp_path: Path, value: str) -> None:
    result = runner.invoke(app, ["scan", str(tmp_path), "--fail-under", value])
    assert result.exit_code == 2


def test_json_threshold_failure_keeps_stdout_machine_readable(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["scan", str(tmp_path), "--format", "json", "--fail-under", "80"],
    )

    assert result.exit_code == 1
    assert json.loads(result.stdout)["score"] == 25


def test_output_file_is_written_before_threshold_failure(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    output = tmp_path / "report.json"

    result = runner.invoke(
        app,
        [
            "scan",
            str(repo),
            "--format",
            "json",
            "--output",
            str(output),
            "--fail-under",
            "80",
        ],
    )

    assert result.exit_code == 1
    assert json.loads(output.read_text(encoding="utf-8"))["score"] == 25


def test_output_io_failure_exits_two(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_write(_path: Path, *_args: object, **_kwargs: object) -> int:
        raise OSError("write failed")

    monkeypatch.setattr(Path, "write_text", fail_write)
    result = runner.invoke(
        app,
        ["scan", str(tmp_path), "--format", "json", "--output", "report.json"],
    )
    assert result.exit_code == 2


@pytest.mark.parametrize("error_type", [OSError, RuntimeError])
def test_output_path_normalization_failure_has_clean_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[Exception],
) -> None:
    sentinel = "OUTPUT_NORMALIZATION_SENTINEL_MUST_NOT_LEAK"

    def fail_normalization(_path: Path) -> Path:
        raise error_type(sentinel)

    monkeypatch.setattr(cli_module, "normalize_local_path", fail_normalization)

    result = runner.invoke(
        app,
        ["scan", str(tmp_path), "--format", "json", "--output", "report.json"],
    )

    assert result.exit_code == 2
    assert result.stdout == ""
    assert result.stderr.startswith("Error: ")
    assert "report output path cannot be normalized" in result.stderr
    assert sentinel not in result.stderr
    assert "Traceback" not in result.stderr


def test_unreadable_repository_error_exits_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_scan(_path: Path, **_kwargs: object) -> None:
        raise RepositoryScanError("Repository path is not readable")

    monkeypatch.setattr(cli_module, "scan_repository", fail_scan)
    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 2


def test_automatic_config_changes_json_findings_and_score(tmp_path: Path) -> None:
    write_policy(
        tmp_path / ".repo-doctor.toml",
        "[checks.readme-exists]\nenabled = false\n[checks.license-exists]\nenabled = false\n",
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

    def guarded_lstat(path: Path, *args: object, **kwargs: object) -> os.stat_result:
        if path == automatic:
            raise AssertionError("automatic policy metadata was inspected")
        return original_lstat(path, *args, **kwargs)

    def guarded_stat(path: Path, *args: object, **kwargs: object) -> os.stat_result:
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
        "[checks.readme-exists]\nenabled = false\n[checks.license-exists]\nenabled = false\n",
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


def test_scan_help_lists_config_option(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")

    result = runner.invoke(app, ["scan", "--help"])
    normalized_stdout = ANSI_ESCAPE_RE.sub("", result.stdout)

    assert result.exit_code == 0
    assert "--config" in normalized_stdout


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


ALL_DISABLED_POLICY = (
    b"version = 1\n"
    b"[checks.readme-exists]\nenabled = false\n"
    b"[checks.readme-sections]\nenabled = false\n"
    b"[checks.license-exists]\nenabled = false\n"
    b"[checks.tests-exist]\nenabled = false\n"
    b"[checks.ci-exists]\nenabled = false\n"
    b"[checks.docker-exists]\nenabled = false\n"
    b"[checks.env-example]\nenabled = false\n"
)


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
def test_invalid_automatic_config_has_clean_error(tmp_path: Path, payload: bytes) -> None:
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
