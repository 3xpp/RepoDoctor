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
    def run(self, repo_path: Path) -> Finding:
        tests_directory = repo_path / "tests"
        passed = (not tests_directory.is_symlink() and tests_directory.is_dir()) or any(
            path.is_file() and any(fnmatch(path.name, pattern) for pattern in TEST_PATTERNS)
            for path in iter_repository_files(repo_path)
        )
        return Finding(
            id="tests-exist",
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
