import os
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from repo_doctor import __version__
from repo_doctor.checks import DEFAULT_CHECKS
from repo_doctor.checks.base import Check
from repo_doctor.models import Report
from repo_doctor.scoring import MAX_SCORE, calculate_score, summarize_score


class RepositoryScanError(ValueError):
    """Raised when a repository path cannot be scanned."""


def scan_repository(
    repo_path: Path,
    *,
    checks: Sequence[Check] = DEFAULT_CHECKS,
    generated_at: datetime | None = None,
) -> Report:
    try:
        resolved = repo_path.expanduser().resolve(strict=True)
    except FileNotFoundError as exc:
        raise RepositoryScanError(f"Repository path does not exist: {repo_path}") from exc
    except (OSError, RuntimeError) as exc:
        raise RepositoryScanError(f"Repository path cannot be accessed: {repo_path}") from exc
    if not resolved.is_dir():
        raise RepositoryScanError(f"Repository path is not a directory: {repo_path}")

    try:
        with os.scandir(resolved):
            pass
    except OSError as exc:
        raise RepositoryScanError(f"Repository path is not readable: {repo_path}") from exc

    try:
        findings = tuple(check.run(resolved) for check in checks)
    except OSError as exc:
        raise RepositoryScanError(f"Repository could not be read completely: {repo_path}") from exc
    score = calculate_score(findings)
    return Report(
        repo_path=str(resolved),
        score=score,
        max_score=MAX_SCORE,
        summary=summarize_score(score),
        findings=findings,
        generated_at=generated_at or datetime.now(UTC),
        version=__version__,
    )
