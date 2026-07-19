from pathlib import Path
from typing import Protocol, runtime_checkable

from repo_doctor.models import Finding


@runtime_checkable
class Check(Protocol):
    @property
    def id(self) -> str:
        """Return the stable finding ID before the check runs."""
        raise NotImplementedError

    def run(
        self,
        repo_path: Path,
        *,
        excluded_paths: frozenset[Path] = frozenset(),
    ) -> Finding:
        """Evaluate one deterministic repository-readiness rule."""
        raise NotImplementedError
