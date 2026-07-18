import re

from repo_doctor.models import Report

LINE_BREAK_RE = re.compile(r"\r\n?|\n")
BACKTICK_RUN_RE = re.compile(r"`+")
MARKDOWN_SPECIALS = frozenset("\\`*_{}[]<>|~")


def _single_line(value: str) -> str:
    normalized = LINE_BREAK_RE.sub(" ", value)
    return "".join(character if character.isprintable() else " " for character in normalized)


def _escape_inline(value: str) -> str:
    normalized = _single_line(value)
    return "".join(
        f"\\{character}" if character in MARKDOWN_SPECIALS else character
        for character in normalized
    )


def _escape_cell(value: str) -> str:
    return _escape_inline(value)


def _code_span(value: str) -> str:
    normalized = _single_line(value)
    if not normalized or normalized.isspace():
        normalized = repr(normalized)
    longest_run = max(
        (len(match.group()) for match in BACKTICK_RUN_RE.finditer(normalized)),
        default=0,
    )
    delimiter = "`" * (longest_run + 1)
    if normalized.startswith(("`", " ")) or normalized.endswith(("`", " ")):
        normalized = f" {normalized} "
    return f"{delimiter}{normalized}{delimiter}"


def render_markdown(report: Report) -> str:
    generated_at = report.generated_at.isoformat().replace("+00:00", "Z")
    lines = [
        "# GitHub Repo Doctor Report",
        "",
        f"- **Repository:** {_code_span(report.repo_path)}",
        f"- **Score:** {report.score}/{report.max_score}",
        f"- **Summary:** {_escape_inline(report.summary)}",
        f"- **Generated:** {_escape_inline(generated_at)}",
        f"- **Version:** {_escape_inline(report.version)}",
        "",
        "## Findings",
        "",
        "| Status | Severity | Category | Check | Description |",
        "| --- | --- | --- | --- | --- |",
    ]
    for finding in report.findings:
        status = "Passed" if finding.passed else "Failed"
        check = f"{finding.title} ({finding.id})"
        lines.append(
            "| "
            + " | ".join(
                _escape_cell(value)
                for value in (
                    status,
                    finding.severity.value,
                    finding.category,
                    check,
                    finding.description,
                )
            )
            + " |"
        )

    lines.extend(["", "## Recommendations", ""])
    failed = [finding for finding in report.findings if not finding.passed]
    if failed:
        lines.extend(
            (f"- **{_escape_inline(finding.title)}:** {_escape_inline(finding.recommendation)}")
            for finding in failed
        )
    else:
        lines.append("- No readiness issues found.")
    return "\n".join(lines) + "\n"
