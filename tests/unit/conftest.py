from datetime import UTC, datetime

import pytest

from repo_doctor.models import Finding, Report, Severity


@pytest.fixture
def fixed_report() -> Report:
    return Report(
        repo_path="/tmp/example",
        score=80,
        max_score=100,
        summary="Good foundation with a few worthwhile improvements.",
        findings=(
            Finding(
                id="license-exists",
                title="License exists",
                description="A recognized root license file is present.",
                severity=Severity.HIGH,
                category="Licensing",
                recommendation="Keep the license file accurate.",
                passed=True,
            ),
            Finding(
                id="readme-exists",
                title="README exists",
                description="No supported root README file was found.",
                severity=Severity.HIGH,
                category="Documentation",
                recommendation="Add README.md with project guidance.",
                passed=False,
            ),
        ),
        generated_at=datetime(2026, 7, 18, 12, tzinfo=UTC),
        version="0.2.0",
    )
