from repo_doctor.checks.readme import ReadmeSectionsCheck


def test_fenced_and_indented_code_headings_are_ignored(tmp_path) -> None:
    (tmp_path / "README.md").write_text(
        "# Installation\n\n"
        "```markdown\n# Usage\n```\n\n"
        "~~~markdown\n# Testing\n~~~\n\n"
        "    # Development\n\n"
        "\t# Contributing\n",
        encoding="utf-8",
    )
    assert ReadmeSectionsCheck().run(tmp_path).passed is False


def test_markdown_does_not_treat_rst_only_adornments_as_headings(tmp_path) -> None:
    (tmp_path / "README.md").write_text(
        "Installation\n************\n\nUsage\n~~~~~~~~\n", encoding="utf-8"
    )
    assert ReadmeSectionsCheck().run(tmp_path).passed is False


def test_rst_only_adornments_remain_supported(tmp_path) -> None:
    (tmp_path / "README.rst").write_text(
        "Installation\n************\n\nUsage\n~~~~~~~~\n", encoding="utf-8"
    )
    assert ReadmeSectionsCheck().run(tmp_path).passed is True
