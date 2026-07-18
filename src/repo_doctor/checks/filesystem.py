from collections.abc import Iterator
from pathlib import Path

EXCLUDED_DIRECTORIES = frozenset({
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    "dist",
    "build",
    "coverage",
    "htmlcov",
})
PROTECTED_BASENAMES = frozenset({
    ".env",
    ".envrc",
    ".npmrc",
    ".pypirc",
    "credentials",
    "credentials.json",
    "secrets.json",
    "secrets.yaml",
    "secrets.yml",
    "secrets.toml",
    "service-account.json",
    "id_rsa",
    "id_ed25519",
})
PROTECTED_SUFFIXES = frozenset({".pem", ".key", ".p12", ".pfx", ".keystore"})


def is_protected_path(path: Path) -> bool:
    name = path.name.casefold()
    return (
        name in PROTECTED_BASENAMES
        or name.startswith(".env.")
        or path.suffix.casefold() in PROTECTED_SUFFIXES
    )


def iter_repository_files(repo_path: Path) -> Iterator[Path]:
    for directory, dir_names, file_names in repo_path.walk(
        top_down=True, follow_symlinks=False
    ):
        dir_names[:] = sorted(
            name
            for name in dir_names
            if name not in EXCLUDED_DIRECTORIES
            and not (directory / name).is_symlink()
        )
        for name in sorted(file_names):
            candidate = directory / name
            if not candidate.is_symlink():
                yield candidate
