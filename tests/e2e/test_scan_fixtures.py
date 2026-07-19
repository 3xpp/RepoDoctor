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
