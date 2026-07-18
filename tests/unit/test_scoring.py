from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from repo_doctor.models import Finding, Report, Severity
from repo_doctor.scoring import MAX_SCORE, calculate_score, summarize_score


def finding(severity: Severity, *, passed: bool = False) -> Finding:
    return Finding(
        id=f"example-{severity.value}",
        title="Example",
        description="Example finding.",
        severity=severity,
        category="Testing",
        recommendation="Fix the example.",
        passed=passed,
    )


@pytest.mark.parametrize(
    ("severity", "expected"),
    [
        (Severity.HIGH, 80),
        (Severity.MEDIUM, 90),
        (Severity.LOW, 95),
        (Severity.INFO, 100),
    ],
)
def test_failed_findings_use_severity_deductions(
    severity: Severity, expected: int
) -> None:
    assert calculate_score([finding(severity)]) == expected


def test_passed_findings_do_not_deduct_points() -> None:
    assert calculate_score([finding(Severity.HIGH, passed=True)]) == MAX_SCORE


def test_score_never_falls_below_zero() -> None:
    assert calculate_score([finding(Severity.HIGH) for _ in range(6)]) == 0


@pytest.mark.parametrize(
    ("score", "phrase"),
    [(90, "Excellent"), (75, "Good"), (50, "Meaningful"), (49, "Substantial")],
)
def test_summary_boundaries(score: int, phrase: str) -> None:
    assert summarize_score(score).startswith(phrase)


def test_report_preserves_required_field_order() -> None:
    report = Report(
        repo_path="/tmp/example",
        score=100,
        max_score=100,
        summary="Excellent readiness.",
        findings=(finding(Severity.INFO, passed=True),),
        generated_at=datetime(2026, 7, 18, tzinfo=UTC),
        version="0.1.0",
    )
    assert list(report.model_dump()) == [
        "repo_path",
        "score",
        "max_score",
        "summary",
        "findings",
        "generated_at",
        "version",
    ]


def test_report_requires_aware_generated_timestamp() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        Report(
            repo_path="/tmp/example",
            score=100,
            max_score=100,
            summary="Excellent readiness.",
            findings=(),
            generated_at=datetime(2026, 7, 18),
            version="0.1.0",
        )


def test_report_normalizes_generated_timestamp_to_utc() -> None:
    report = Report(
        repo_path="/tmp/example",
        score=100,
        max_score=100,
        summary="Excellent readiness.",
        findings=(),
        generated_at=datetime(
            2026, 7, 18, 14, tzinfo=timezone(timedelta(hours=2))
        ),
        version="0.1.0",
    )
    assert report.generated_at == datetime(2026, 7, 18, 12, tzinfo=UTC)
