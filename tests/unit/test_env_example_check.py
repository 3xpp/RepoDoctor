from pathlib import Path

import repo_doctor.checks.env_example as env_module
from repo_doctor.checks.env_example import EnvExampleCheck
from repo_doctor.scanner import scan_repository


def test_env_example_is_not_required_without_env_usage(tmp_path) -> None:
    (tmp_path / "app.py").write_text("print('hello')\n", encoding="utf-8")
    assert EnvExampleCheck().run(tmp_path).passed is True


def test_env_example_is_required_when_usage_is_detected(tmp_path) -> None:
    (tmp_path / "app.py").write_text("import os\nMODE = os.getenv('APP_MODE')\n", encoding="utf-8")
    assert EnvExampleCheck().run(tmp_path).passed is False
    (tmp_path / ".env.example").touch()
    assert EnvExampleCheck().run(tmp_path).passed is True


def test_config_interpolation_is_not_applied_to_source_files(tmp_path) -> None:
    (tmp_path / "app.py").write_text("template = '${NOT_ENV_CONFIGURATION}'\n", encoding="utf-8")
    assert EnvExampleCheck().run(tmp_path).passed is True


def test_undecodable_candidate_is_skipped(tmp_path) -> None:
    (tmp_path / "app.py").write_bytes(b"\xffos.getenv('APP_MODE')\n")
    assert EnvExampleCheck().run(tmp_path).passed is True


def test_effective_policy_is_excluded_from_environment_detection(tmp_path: Path) -> None:
    policy = tmp_path / ".repo-doctor.toml"
    policy.write_text("version = 1\n# env_file: .env\n", encoding="utf-8")
    finding = EnvExampleCheck().run(tmp_path, excluded_paths=frozenset({policy}))
    assert finding.passed is True


def test_other_toml_environment_signal_still_requires_example(tmp_path: Path) -> None:
    (tmp_path / "application.toml").write_text("# ${APP_TOKEN}\n", encoding="utf-8")
    finding = EnvExampleCheck().run(tmp_path, excluded_paths=frozenset())
    assert finding.passed is False


def test_excluded_readme_policy_does_not_shadow_genuine_readme(tmp_path: Path) -> None:
    policy = tmp_path / "README.md"
    policy.write_text("version = 1\n", encoding="utf-8")
    (tmp_path / "README.rst").write_text(
        "Setup\n=====\n\nCopy ``.env`` before running the project.\n",
        encoding="utf-8",
    )

    finding = EnvExampleCheck().run(
        tmp_path,
        excluded_paths=frozenset({policy}),
    )

    assert finding.passed is False


def test_full_scanner_never_reads_protected_env_path(tmp_path, monkeypatch) -> None:
    protected = (tmp_path / ".env", tmp_path / ".env.example")
    monkeypatch.setattr(
        env_module,
        "_iter_candidate_files",
        lambda _repo, *, excluded_paths=frozenset(): iter(protected),
    )

    original_read_text = Path.read_text

    def guarded_read_text(path: Path, *args, **kwargs) -> str:
        if path.name.startswith(".env"):
            raise AssertionError("scanner attempted to read a protected environment file")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    report = scan_repository(tmp_path)
    assert len(report.findings) == 7
