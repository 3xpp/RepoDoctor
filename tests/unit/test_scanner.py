from datetime import UTC, datetime
from pathlib import Path

import pytest

import repo_doctor.scanner as scanner_module
from repo_doctor.scanner import RepositoryScanError, scan_repository


def test_empty_repository_has_ordered_findings_and_low_score(tmp_path) -> None:
    report = scan_repository(tmp_path, generated_at=datetime(2026, 7, 18, tzinfo=UTC))
    assert [finding.id for finding in report.findings] == [
        "readme-exists",
        "readme-sections",
        "license-exists",
        "tests-exist",
        "ci-exists",
        "docker-exists",
        "env-example",
    ]
    assert report.score == 25
    assert report.repo_path == str(tmp_path.resolve())


def test_scanner_rejects_missing_path(tmp_path) -> None:
    with pytest.raises(RepositoryScanError, match="does not exist"):
        scan_repository(tmp_path / "missing")


def test_scanner_wraps_resolution_permission_error(tmp_path, monkeypatch) -> None:
    def deny_resolve(_path, *, strict: bool):
        raise PermissionError("permission denied")

    monkeypatch.setattr(Path, "resolve", deny_resolve)
    with pytest.raises(RepositoryScanError, match="cannot be accessed"):
        scan_repository(tmp_path)


def test_scanner_rejects_unreadable_directory(tmp_path, monkeypatch) -> None:
    def deny_scan(_path):
        raise PermissionError("permission denied")

    monkeypatch.setattr(scanner_module.os, "scandir", deny_scan)
    with pytest.raises(RepositoryScanError, match="not readable"):
        scan_repository(tmp_path)
