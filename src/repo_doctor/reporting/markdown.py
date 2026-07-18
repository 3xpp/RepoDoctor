from repo_doctor.models import Report


def _escape_cell(value: str) -> str:
    return value.replace("|", r"\|").replace("\n", " ")


def render_markdown(report: Report) -> str:
    generated_at = report.generated_at.isoformat().replace("+00:00", "Z")
    lines = [
        "# GitHub Repo Doctor Report",
        "",
        f"- **Repository:** `{report.repo_path}`",
        f"- **Score:** {report.score}/{report.max_score}",
        f"- **Summary:** {report.summary}",
        f"- **Generated:** {generated_at}",
        f"- **Version:** {report.version}",
        "",
        "## Findings",
        "",
        "| Status | Severity | Category | Check | Description |",
        "| --- | --- | --- | --- | --- |",
    ]
    for finding in report.findings:
        status = "Passed" if finding.passed else "Failed"
        check = f"{finding.title} (`{finding.id}`)"
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
        lines.extend(f"- **{finding.title}:** {finding.recommendation}" for finding in failed)
    else:
        lines.append("- No readiness issues found.")
    return "\n".join(lines) + "\n"
