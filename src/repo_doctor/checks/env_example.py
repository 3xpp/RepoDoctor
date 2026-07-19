import re
from collections.abc import Iterator
from pathlib import Path

from repo_doctor.checks.filesystem import (
    is_protected_path,
    iter_repository_files,
)
from repo_doctor.checks.readme import find_readme
from repo_doctor.models import Finding, Severity

MAX_TEXT_FILE_BYTES = 1024 * 1024
SOURCE_SUFFIXES = frozenset(
    {
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".mjs",
        ".cjs",
        ".sh",
    }
)
CONFIG_SUFFIXES = frozenset(
    {
        ".toml",
        ".yaml",
        ".yml",
        ".json",
        ".ini",
        ".cfg",
        ".conf",
    }
)
TEXT_SUFFIXES = SOURCE_SUFFIXES | CONFIG_SUFFIXES
COMPOSE_NAMES = frozenset(
    {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}
)
ENV_TOKENS = (
    "os.environ",
    "os.getenv(",
    "process.env",
    "import.meta.env",
    "load_dotenv(",
    "dotenv.config(",
    "from dotenv",
    "import dotenv",
)
INTERPOLATION_RE = re.compile(r"\$\{[A-Z_][A-Z0-9_]*\}")
README_ENV_RE = re.compile(
    r"(?:^|[\s`'\"])\.env(?:\.example)?(?=$|[\s`'\",.;:])",
    re.MULTILINE,
)


def _iter_candidate_files(repo_path: Path) -> Iterator[Path]:
    return iter_repository_files(repo_path)


def _path_has_env_usage(
    path: Path,
    readme_path: Path | None,
    repo_path: Path,
) -> bool:
    if is_protected_path(path):
        return False
    name = path.name.casefold()
    is_root_compose = path.parent == repo_path and name in COMPOSE_NAMES
    if path != readme_path and not is_root_compose and path.suffix.casefold() not in TEXT_SUFFIXES:
        return False
    if path.is_symlink():
        return False
    try:
        if not path.is_file() or path.stat().st_size > MAX_TEXT_FILE_BYTES:
            return False
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False
    if path == readme_path:
        return README_ENV_RE.search(text) is not None
    if any(token in text for token in ENV_TOKENS):
        return True
    if is_root_compose or path.suffix.casefold() in CONFIG_SUFFIXES:
        if "env_file:" in text or INTERPOLATION_RE.search(text):
            return True
    return False


def _has_env_example(repo_path: Path) -> bool:
    return any(
        entry.name.casefold() == ".env.example" and not entry.is_symlink() and entry.is_file()
        for entry in repo_path.iterdir()
    )


class EnvExampleCheck:
    @property
    def id(self) -> str:
        return "env-example"

    def run(
        self,
        repo_path: Path,
        *,
        excluded_paths: frozenset[Path] = frozenset(),
    ) -> Finding:
        readme = find_readme(repo_path)
        usage_detected = any(
            _path_has_env_usage(path, readme, repo_path)
            for path in _iter_candidate_files(repo_path)
        )
        example_exists = _has_env_example(repo_path)
        passed = not usage_detected or example_exists
        if not usage_detected:
            description = "No environment-variable usage was detected."
            recommendation = "No action required; add .env.example if configuration is introduced."
        elif example_exists:
            description = "Environment usage and a root .env.example were detected."
            recommendation = "Keep placeholder names aligned with required configuration."
        else:
            description = "Environment usage was detected without a root .env.example."
            recommendation = "Add .env.example with placeholder names and no real secret values."
        return Finding(
            id=self.id,
            title="Environment example is documented",
            description=description,
            severity=Severity.MEDIUM,
            category="Configuration",
            recommendation=recommendation,
            passed=passed,
        )
