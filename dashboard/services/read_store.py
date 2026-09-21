import json
import sqlite3
from contextlib import contextmanager
from seed.paths import checked_path


class ServiceError(Exception):
    def __init__(self, code, message, status=422):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def decode(value, default=None):
    try:
        return json.loads(value, parse_constant=lambda value: None)
    except (ValueError, TypeError):
        return default


class ReadStore:
    def __init__(self, home):
        self.home = home

    @contextmanager
    def connection(self, write=False):
        try:
            path = checked_path(self.home, 'memory.sqlite3')
            for suffix in ('-wal', '-shm', '-journal'):
                checked_path(self.home, 'memory.sqlite3' + suffix)
            if not path.is_file():
                raise ServiceError('missing_database', 'No SEED memory database is available yet.', 503)
            db = sqlite3.connect(path.as_uri() + ('?mode=rw' if write else '?mode=ro'), uri=True, timeout=1)
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA foreign_keys=ON')
            try:
                yield db
                if write:
                    db.commit()
            except BaseException:
                if write:
                    db.rollback()
                raise
            finally:
                db.close()
        except sqlite3.Error as error:
            raise ServiceError('database_unavailable', 'SEED database is busy, damaged, or incompatible.', 503) from error
        except (OSError, ValueError) as error:
            raise ServiceError('unsafe_storage', 'SEED storage is unavailable or uses unsupported symlinks.', 503) from error

    @staticmethod
    def tables(db):
        return {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
