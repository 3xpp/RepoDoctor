from pathlib import Path

from repo_doctor.models import Finding, Severity


class GitHubActionsCheck:
    @property
    def id(self) -> str:
        return "ci-exists"

    def run(
        self,
        repo_path: Path,
        *,
        excluded_paths: frozenset[Path] = frozenset(),
    ) -> Finding:
        github_directory = repo_path / ".github"
        workflows = repo_path / ".github" / "workflows"
        passed = (
            not github_directory.is_symlink()
            and not workflows.is_symlink()
            and workflows.is_dir()
            and any(
                not path.is_symlink()
                and path.is_file()
                and path.suffix.casefold() in {".yml", ".yaml"}
                for path in workflows.iterdir()
            )
        )
        return Finding(
            id=self.id,
            title="GitHub Actions workflow exists",
            description=(
                "At least one GitHub Actions workflow is present."
                if passed
                else "No GitHub Actions YAML workflow was found."
            ),
            severity=Severity.MEDIUM,
            category="Automation",
            recommendation=(
                "Keep CI aligned with supported development workflows."
                if passed
                else "Add a workflow under .github/workflows to run project checks."
            ),
            passed=passed,
        )
