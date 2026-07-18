import re

from rich.console import Console
from rich.text import Text

from repo_doctor.models import Report, Severity

LINE_BREAK_RE = re.compile(r"\r\n?|\n")
SEVERITY_ORDER = (
    Severity.HIGH,
    Severity.MEDIUM,
    Severity.LOW,
    Severity.INFO,
)
SEVERITY_STYLES = {
    Severity.HIGH: "bold red",
    Severity.MEDIUM: "bold yellow",
    Severity.LOW: "bold blue",
    Severity.INFO: "bold cyan",
}


def _single_line(value: str) -> str:
    normalized = LINE_BREAK_RE.sub(" ", value)
    return "".join(character if character.isprintable() else " " for character in normalized)


def render_terminal(report: Report, console: Console | None = None) -> None:
    target = console or Console()
    target.print("Repository readiness", style="bold cyan")
    target.print(f"{report.score}/{report.max_score}", style="bold")
    target.print(Text(_single_line(report.summary)))
    target.print(Text(f"Repository: {_single_line(report.repo_path)}"))
    passed_count = sum(finding.passed for finding in report.findings)
    target.print(f"{passed_count}/{len(report.findings)} checks passed")

    failures = [finding for finding in report.findings if not finding.passed]
    if not failures:
        target.print("No readiness issues found.", style="green")
        return

    for severity in SEVERITY_ORDER:
        grouped = [finding for finding in failures if finding.severity == severity]
        if not grouped:
            continue
        target.print()
        target.print(
            f"{severity.value.upper()} findings",
            style=SEVERITY_STYLES[severity],
        )
        for finding in grouped:
            title = _single_line(finding.title)
            recommendation = _single_line(finding.recommendation)
            target.print(Text(f"- {title}: {recommendation}"))
