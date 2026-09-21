"""Storage paths are restricted to an owner-selected SEED home."""
from pathlib import Path


def checked_path(home: Path, relative: str) -> Path:
    home = Path(home).absolute()
    part = Path(relative)
    if part.is_absolute() or '..' in part.parts:
        raise ValueError('Path must remain inside SEED home')
    path = home / part
    for parent in [path, *path.parents]:
        if parent.is_symlink():
            raise ValueError('Symlink storage paths are not supported')
    return path
