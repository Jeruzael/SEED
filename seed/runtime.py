"""Single instance ownership, with a session token bound to the locked file."""
import fcntl
import json
import os
from pathlib import Path
from .paths import checked_path


class InstanceLock:
    def __init__(self, path: Path):
        self.path = checked_path(path.parent, path.name)
        self.file = None

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        self.file = os.fdopen(fd, 'r+')
        try:
            fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self.file.close()
            self.file = None
            raise RuntimeError('SEED already has an active instance') from None
        return self

    def identify(self, session_id: str):
        self.file.seek(0)
        self.file.truncate()
        json.dump({'session_id': session_id, 'pid': os.getpid()}, self.file)
        self.file.flush()

    def close(self):
        if self.file:
            fcntl.flock(self.file, fcntl.LOCK_UN)
            self.file.close()
            self.file = None

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *args):
        self.close()


def owner(path: Path) -> dict | None:
    """Read lock identity without creating a file; PID alone is not ownership."""
    path = checked_path(path.parent, path.name)
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    except FileNotFoundError:
        return None
    with os.fdopen(fd, 'r') as file:
        try:
            fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            try:
                data = json.load(file)
                return data if isinstance(data, dict) else None
            except (ValueError, OSError):
                return None
        else:
            fcntl.flock(file, fcntl.LOCK_UN)
            return None
