import pytest
from rich.console import Console

from repo_doctor.models import Finding, Report, Severity
from repo_doctor.reporting.markdown import _code_span, render_markdown
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


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("", "`''`"),
        (" ", "`' '`"),
        ("`edge`", "`` `edge` ``"),
        (" leading ", "`  leading  `"),
    ],
)
def test_code_span_handles_empty_whitespace_and_edge_backticks(
    value: str,
    expected: str,
) -> None:
    assert _code_span(value) == expected


def test_markdown_safely_renders_adversarial_dynamic_values(
    fixed_report: Report,
) -> None:
    finding = Finding(
        id="check|id",
        title="Café *title*",
        description="First\r\n| second",
        severity=Severity.MEDIUM,
        category="Docs_[external]",
        recommendation="Fix this\n- injected [link](https://example.invalid)",
        passed=False,
    )
    report = fixed_report.model_copy(
        update={
            "repo_path": "/tmp/re`po``\n# injected",
            "summary": "Café\rsummary *bold* ~~strike~~",
            "findings": (finding,),
        }
    )

    rendered = render_markdown(report)

    assert "```/tmp/re`po`` # injected```" in rendered
    assert "\n# injected" not in rendered
    assert "\n- injected" not in rendered
    assert r"Café summary \*bold\* \~\~strike\~\~" in rendered
    assert r"Café \*title\*" in rendered
    assert r"check\|id" in rendered
    assert r"First \| second" in rendered
    assert r"Fix this - injected \[link\]" in rendered
    assert rendered.endswith("\n")


def test_terminal_focuses_on_failed_findings(fixed_report: Report) -> None:
    console = Console(record=True, color_system=None, width=120)
    render_terminal(fixed_report, console)
    rendered = console.export_text()
    assert "80/100" in rendered
    assert "1/2 checks passed" in rendered
    assert "README exists" in rendered
    assert "License exists" not in rendered


def test_terminal_treats_summary_as_literal_and_handles_all_passed(
    fixed_report: Report,
) -> None:
    report = fixed_report.model_copy(
        update={
            "score": 100,
            "summary": "[/bold] Café",
            "findings": tuple(
                finding.model_copy(update={"passed": True}) for finding in fixed_report.findings
            ),
        }
    )
    console = Console(record=True, color_system=None, width=120)

    render_terminal(report, console)
    rendered = console.export_text()

    assert "[/bold] Café" in rendered
    assert "No readiness issues found." in rendered


def test_terminal_normalizes_dynamic_control_characters(
    fixed_report: Report,
) -> None:
    finding = fixed_report.findings[1].model_copy(
        update={
            "title": "Real\nFAKE TITLE",
            "recommendation": "Fix\r\nFAKE RECOMMENDATION\tNOW",
        }
    )
    report = fixed_report.model_copy(
        update={
            "summary": "Summary\nFAKE SUMMARY",
            "repo_path": "/tmp/repo\rFAKE PATH",
            "findings": (finding,),
        }
    )
    console = Console(record=True, color_system=None, width=120)

    render_terminal(report, console)
    rendered = console.export_text()

    assert "Summary FAKE SUMMARY" in rendered
    assert "Repository: /tmp/repo FAKE PATH" in rendered
    assert "- Real FAKE TITLE: Fix FAKE RECOMMENDATION NOW" in rendered
    assert "\nFAKE" not in rendered


def test_terminal_keeps_logical_lines_unbroken_at_narrow_width(
    fixed_report: Report,
) -> None:
    repository = "/tmp/a-repository-path-that-is-much-wider-than-the-console"
    recommendation = "Add a detailed installation guide with prerequisites and verification steps."
    finding = fixed_report.findings[1].model_copy(
        update={"title": "README guidance", "recommendation": recommendation}
    )
    report = fixed_report.model_copy(update={"repo_path": repository, "findings": (finding,)})
    console = Console(record=True, color_system=None, width=20)

    render_terminal(report, console)
    rendered = console.export_text()

    assert f"Repository: {repository}\n" in rendered
    assert f"- README guidance: {recommendation}\n" in rendered


def test_terminal_groups_failures_in_severity_order(fixed_report: Report) -> None:
    base = fixed_report.findings[1]
    findings = tuple(
        base.model_copy(
            update={
                "id": severity.value,
                "title": f"{severity.value} issue",
                "severity": severity,
            }
        )
        for severity in (
            Severity.INFO,
            Severity.LOW,
            Severity.MEDIUM,
            Severity.HIGH,
        )
    )
    report = fixed_report.model_copy(update={"findings": findings})
    console = Console(record=True, color_system=None, width=120)

    render_terminal(report, console)
    rendered = console.export_text()

    positions = [
        rendered.index(f"{severity.value.upper()} findings")
        for severity in (
            Severity.HIGH,
            Severity.MEDIUM,
            Severity.LOW,
            Severity.INFO,
        )
    ]
    assert positions == sorted(positions)
