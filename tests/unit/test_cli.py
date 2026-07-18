import json
import os
from pathlib import Path

import pytest
from typer.testing import CliRunner

import repo_doctor.cli as cli_module
from repo_doctor.cli import app
from repo_doctor.scanner import RepositoryScanError

runner = CliRunner()


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


def test_unreadable_repository_error_exits_two(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_scan(_path: Path) -> None:
        raise RepositoryScanError("Repository path is not readable")

    monkeypatch.setattr(cli_module, "scan_repository", fail_scan)
    result = runner.invoke(app, ["scan", str(tmp_path)])
    assert result.exit_code == 2
