import json
from pathlib import Path

from typer.testing import CliRunner

from repo_doctor.cli import app
from repo_doctor.scanner import scan_repository

FIXTURES = Path(__file__).parents[1] / "fixtures"
PROJECT_ROOT = Path(__file__).parents[2]
runner = CliRunner()


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
    assert sum(finding["passed"] for finding in payload["findings"]) == 5
    assert len(payload["findings"]) == 7
    assert payload["version"] == default_report.version == "0.2.0"
