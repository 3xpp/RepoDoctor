from collections.abc import Sequence

from repo_doctor.models import Finding, Severity

MAX_SCORE = 100
DEDUCTIONS: dict[Severity, int] = {
    Severity.INFO: 0,
    Severity.LOW: 5,
    Severity.MEDIUM: 10,
    Severity.HIGH: 20,
}


def calculate_score(findings: Sequence[Finding]) -> int:
    deduction = sum(DEDUCTIONS[item.severity] for item in findings if not item.passed)
    return max(0, MAX_SCORE - deduction)


def summarize_score(score: int) -> str:
    if score >= 90:
        return "Excellent readiness with strong open-source hygiene."
    if score >= 75:
        return "Good foundation with a few worthwhile improvements."
    if score >= 50:
        return "Meaningful readiness gaps should be addressed."
    return "Substantial work is recommended before sharing this repository."
