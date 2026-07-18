from rich.console import Console

from repo_doctor.models import Report
from repo_doctor.reporting.markdown import render_markdown
from repo_doctor.reporting.terminal import render_terminal


def test_markdown_contains_all_findings_and_failed_recommendations(
    fixed_report: Report,
) -> None:
    rendered = render_markdown(fixed_report)
    assert rendered.endswith("\n")
    assert "80/100" in rendered
    assert "license-exists" in rendered
    assert "readme-exists" in rendered
    assert "Passed" in rendered
    assert "Failed" in rendered
    assert "Add README.md with project guidance." in rendered


def test_terminal_focuses_on_failed_findings(fixed_report: Report) -> None:
    console = Console(record=True, color_system=None, width=120)
    render_terminal(fixed_report, console)
    rendered = console.export_text()
    assert "80/100" in rendered
    assert "1/2 checks passed" in rendered
    assert "README exists" in rendered
    assert "License exists" not in rendered
