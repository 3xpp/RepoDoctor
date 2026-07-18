import json
from pathlib import Path

from typer.testing import CliRunner

from repo_doctor.cli import app
from repo_doctor.scanner import scan_repository

FIXTURES = Path(__file__).parents[1] / "fixtures"
runner = CliRunner()


def test_good_fixture_has_high_score() -> None:
    report = scan_repository(FIXTURES / "good_repo")
    assert report.score >= 90
    assert all(finding.passed for finding in report.findings)


def test_bad_fixture_has_low_score() -> None:
    report = scan_repository(FIXTURES / "bad_repo")
    assert report.score < 50


def test_fixture_json_cli_output_is_valid() -> None:
    result = runner.invoke(app, ["scan", str(FIXTURES / "good_repo"), "--format", "json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout)["score"] >= 90


def test_bad_fixture_fails_requested_threshold() -> None:
    result = runner.invoke(app, ["scan", str(FIXTURES / "bad_repo"), "--fail-under", "80"])
    assert result.exit_code == 1
