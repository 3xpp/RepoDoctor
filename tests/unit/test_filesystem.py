from pathlib import Path

from repo_doctor.checks.filesystem import is_protected_path, iter_repository_files


def test_is_protected_path_detects_protected_ancestor_components() -> None:
    assert is_protected_path(Path("project/.env/config.py")) is True
    assert is_protected_path(Path("project/credentials/settings.json")) is True
    assert is_protected_path(Path("project/src/settings.py")) is False


def test_repository_traversal_prunes_protected_directories(tmp_path) -> None:
    safe_file = tmp_path / "src" / "app.py"
    safe_file.parent.mkdir()
    safe_file.write_text("# Safe fixture.\n", encoding="utf-8")

    env_file = tmp_path / ".env" / "config.py"
    env_file.parent.mkdir()
    env_file.write_text("# Placeholder only.\n", encoding="utf-8")

    credentials_file = tmp_path / "credentials" / "settings.json"
    credentials_file.parent.mkdir()
    credentials_file.write_text("{}\n", encoding="utf-8")

    discovered = [path.relative_to(tmp_path) for path in iter_repository_files(tmp_path)]

    assert discovered == [Path("src/app.py")]
