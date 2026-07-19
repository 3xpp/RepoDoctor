import os
from collections.abc import Collection, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path

from repo_doctor import __version__
from repo_doctor.checks import DEFAULT_CHECKS
from repo_doctor.checks.base import Check
from repo_doctor.models import Report, Severity
from repo_doctor.scoring import DEDUCTIONS, MAX_SCORE, calculate_score, summarize_score


class RepositoryScanError(ValueError):
    """Raised when a repository path cannot be scanned."""


def resolve_repository_path(repo_path: Path) -> Path:
    try:
        resolved = repo_path.expanduser().resolve(strict=True)
    except FileNotFoundError as error:
        raise RepositoryScanError(f"Repository path does not exist: {repo_path}") from error
    except (OSError, RuntimeError) as error:
        raise RepositoryScanError(f"Repository path cannot be accessed: {repo_path}") from error
    if not resolved.is_dir():
        raise RepositoryScanError(f"Repository path is not a directory: {repo_path}")
    try:
        with os.scandir(resolved):
            pass
    except OSError as error:
        raise RepositoryScanError(f"Repository path is not readable: {repo_path}") from error
    return resolved


def scan_repository(
    repo_path: Path,
    *,
    checks: Sequence[Check] = DEFAULT_CHECKS,
    deductions: Mapping[Severity, int] = DEDUCTIONS,
    excluded_paths: Collection[Path] = (),
    generated_at: datetime | None = None,
) -> Report:
    resolved = resolve_repository_path(repo_path)
    exclusions = frozenset(excluded_paths)
    try:
        findings = tuple(check.run(resolved, excluded_paths=exclusions) for check in checks)
    except OSError as error:
        raise RepositoryScanError(
            f"Repository could not be read completely: {repo_path}"
        ) from error
    score = calculate_score(findings, deductions=deductions)
    return Report(
        repo_path=str(resolved),
        score=score,
        max_score=MAX_SCORE,
        summary=summarize_score(score),
        findings=findings,
        generated_at=generated_at or datetime.now(UTC),
        version=__version__,
    )
