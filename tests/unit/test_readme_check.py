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
