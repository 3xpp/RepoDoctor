from pathlib import Path

import pytest

from repo_doctor.checks.readme import ReadmeExistsCheck, ReadmeSectionsCheck


def test_readme_check_detects_missing_readme(tmp_path) -> None:
    assert ReadmeExistsCheck().run(tmp_path).passed is False


@pytest.mark.parametrize("name", ["README.md", "README.rst", "README", "readme.MD"])
def test_readme_check_accepts_supported_names(tmp_path, name: str) -> None:
    (tmp_path / name).write_text("# Installation\n\n## Usage\n", encoding="utf-8")
    assert ReadmeExistsCheck().run(tmp_path).passed is True


def test_useful_sections_require_two_recognized_headings(tmp_path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("# Installation\n", encoding="utf-8")
    assert ReadmeSectionsCheck().run(tmp_path).passed is False
    readme.write_text("# Installation\n\n## Quick Start\n", encoding="utf-8")
    assert ReadmeSectionsCheck().run(tmp_path).passed is True


def test_markdown_and_rst_underlined_headings_are_recognized(tmp_path) -> None:
    (tmp_path / "README.rst").write_text(
        "Installation\n============\n\nUsage\n-----\n", encoding="utf-8"
    )
    assert ReadmeSectionsCheck().run(tmp_path).passed is True


def test_readme_priority_is_deterministic(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# Installation\n", encoding="utf-8")
    (tmp_path / "README.rst").write_text(
        "Installation\n============\n\nUsage\n-----\n", encoding="utf-8"
    )
    assert ReadmeSectionsCheck().run(tmp_path).passed is False


def test_excluded_readme_policy_is_rejected_before_metadata_or_content(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy = tmp_path / "README.md"
    policy.write_text("version = 1\n", encoding="utf-8")
    excluded_paths = frozenset({policy})

    original_is_symlink = Path.is_symlink
    original_is_file = Path.is_file
    original_read_text = Path.read_text

    def guarded_is_symlink(path: Path) -> bool:
        if path == policy:
            raise AssertionError("excluded policy symlink metadata was inspected")
        return original_is_symlink(path)

    def guarded_is_file(path: Path) -> bool:
        if path == policy:
            raise AssertionError("excluded policy file metadata was inspected")
        return original_is_file(path)

    def guarded_read_text(path: Path, *args, **kwargs) -> str:
        if path == policy:
            raise AssertionError("excluded policy content was read")
        return original_read_text(path, *args, **kwargs)

    monkeypatch.setattr(Path, "is_symlink", guarded_is_symlink)
    monkeypatch.setattr(Path, "is_file", guarded_is_file)
    monkeypatch.setattr(Path, "read_text", guarded_read_text)

    assert (
        ReadmeExistsCheck()
        .run(
            tmp_path,
            excluded_paths=excluded_paths,
        )
        .passed
        is False
    )
    assert (
        ReadmeSectionsCheck()
        .run(
            tmp_path,
            excluded_paths=excluded_paths,
        )
        .passed
        is False
    )
