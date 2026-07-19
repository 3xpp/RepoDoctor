from pathlib import Path

from repo_doctor.models import Finding, Severity

DOCKER_FILES = frozenset(
    {
        "Dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "compose.yml",
        "compose.yaml",
    }
)


class DockerCheck:
    @property
    def id(self) -> str:
        return "docker-exists"

    def run(
        self,
        repo_path: Path,
        *,
        excluded_paths: frozenset[Path] = frozenset(),
    ) -> Finding:
        passed = any(
            not (repo_path / name).is_symlink() and (repo_path / name).is_file()
            for name in DOCKER_FILES
        )
        return Finding(
            id=self.id,
            title="Docker setup exists",
            description=(
                "A supported Docker or Compose file is present."
                if passed
                else "No supported Docker or Compose file was found."
            ),
            severity=Severity.LOW,
            category="Operations",
            recommendation=(
                "Keep container setup synchronized with local setup."
                if passed
                else "Consider adding a Dockerfile or Compose file for reproducible setup."
            ),
            passed=passed,
        )
