from pathlib import Path
from typing import Protocol, runtime_checkable

from repo_doctor.models import Finding


@runtime_checkable
class Check(Protocol):
    def run(self, repo_path: Path) -> Finding:
        """Evaluate one deterministic repository-readiness rule."""
        raise NotImplementedError
