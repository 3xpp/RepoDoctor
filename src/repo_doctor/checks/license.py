from pathlib import Path

from repo_doctor.models import Finding, Severity

LICENSE_NAMES = frozenset(
    {
        "license",
        "license.md",
        "license.txt",
        "licence",
        "licence.md",
        "licence.txt",
        "copying",
        "copying.md",
        "copying.txt",
        "unlicense",
    }
)


class LicenseCheck:
    @property
    def id(self) -> str:
        return "license-exists"

    def run(
        self,
        repo_path: Path,
        *,
        excluded_paths: frozenset[Path] = frozenset(),
    ) -> Finding:
        passed = any(
            not entry.is_symlink() and entry.is_file() and entry.name.casefold() in LICENSE_NAMES
            for entry in repo_path.iterdir()
        )
        return Finding(
            id=self.id,
            title="License exists",
            description=(
                "A recognized root license file is present."
                if passed
                else "No recognized root license file was found."
            ),
            severity=Severity.HIGH,
            category="Licensing",
            recommendation=(
                "Keep the license file accurate."
                if passed
                else "Add an OSI-approved license file such as LICENSE."
            ),
            passed=passed,
        )
