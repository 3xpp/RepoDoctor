from fnmatch import fnmatch
from pathlib import Path

from repo_doctor.checks.filesystem import iter_repository_files
from repo_doctor.models import Finding, Severity

TEST_PATTERNS = (
    "test_*.py",
    "*_test.py",
    "*.test.js",
    "*.test.jsx",
    "*.test.ts",
    "*.test.tsx",
    "*.spec.js",
    "*.spec.jsx",
    "*.spec.ts",
    "*.spec.tsx",
)


class TestsCheck:
    @property
    def id(self) -> str:
        return "tests-exist"

    def run(
        self,
        repo_path: Path,
        *,
        excluded_paths: frozenset[Path] = frozenset(),
    ) -> Finding:
        tests_directory = repo_path / "tests"
        passed = (not tests_directory.is_symlink() and tests_directory.is_dir()) or any(
            path.is_file() and any(fnmatch(path.name, pattern) for pattern in TEST_PATTERNS)
            for path in iter_repository_files(
                repo_path,
                excluded_paths=excluded_paths,
            )
        )
        return Finding(
            id=self.id,
            title="Tests exist",
            description=(
                "A tests directory or recognized test file is present."
                if passed
                else "No tests directory or recognized test file was found."
            ),
            severity=Severity.MEDIUM,
            category="Testing",
            recommendation=(
                "Keep automated tests representative of project behavior."
                if passed
                else "Add a tests directory or conventionally named test files."
            ),
            passed=passed,
        )
