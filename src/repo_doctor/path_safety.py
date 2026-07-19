import os
import stat
from pathlib import Path


def normalize_local_path(path: Path, *, expand_user: bool = False) -> Path:
    candidate = path.expanduser() if expand_user else path
    return Path(os.path.abspath(os.path.normpath(os.fspath(candidate))))


def has_symlink_component(path: Path) -> bool:
    candidate = Path(path.anchor)
    for part in path.parts[1:]:
        candidate /= part
        try:
            mode = candidate.lstat().st_mode
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(mode):
            return True
    return False
