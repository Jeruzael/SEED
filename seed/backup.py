"""Consistent SQLite snapshots shared by core upgrade and dashboard. Standard library only."""
import json
import os
import sqlite3
import tempfile
import time
import uuid
from .paths import checked_path
from .runtime import InstanceLock


def read_manifest(home):
    path = checked_path(home, 'backups/manifest.json')
    if not path.exists():
        return []
    with path.open() as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError('Invalid backup manifest')
    return data


def write_manifest(home, entries):
    path = checked_path(home, 'backups/manifest.json')
    temp = checked_path(home, 'backups/.manifest-' + uuid.uuid4().hex)
    fd = os.open(temp, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'w') as file:
            json.dump(entries, file)
            file.flush()
            os.fsync(file.fileno())
        checked_path(home, 'backups/manifest.json')
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def create_backup(home):
    source_path = checked_path(home, 'memory.sqlite3')
    for suffix in ('-wal','-shm','-journal'):
        checked_path(home, 'memory.sqlite3' + suffix)
    if not source_path.is_file():
        raise ValueError('No memory database to back up')
    directory = checked_path(home, 'backups')
    directory.mkdir(mode=0o700, exist_ok=True)
    with InstanceLock(checked_path(home, 'backup.lock')):
        entries = read_manifest(home)
        name = time.strftime('memory-%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:12] + '.sqlite3'
        destination = checked_path(home, 'backups/' + name)
        fd, temp_name = tempfile.mkstemp(prefix='.pending-', suffix='.sqlite3', dir=directory)
        os.close(fd)
        temp = checked_path(home, 'backups/' + os.path.basename(temp_name))
        started = time.monotonic()
        def progress(status, remaining, total):
            if time.monotonic() - started > 15:
                raise TimeoutError('Backup exceeded its time budget; no snapshot was published')
        try:
            with sqlite3.connect(source_path.as_uri() + '?mode=rw', uri=True, timeout=1) as source:
                try:
                    source.execute('PRAGMA wal_checkpoint(PASSIVE)').fetchall()
                except sqlite3.OperationalError:
                    pass
                target = sqlite3.connect(temp)
                try:
                    source.backup(target, pages=128, progress=progress, sleep=.05)
                    if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                        raise ValueError('Backup integrity verification failed')
                finally:
                    target.close()
            checked_path(home, 'backups/' + name)
            os.replace(temp, destination)
            result = {'name':name, 'bytes':destination.stat().st_size, 'created_at':time.time(), 'integrity':'ok'}
            entries.append(result)
            write_manifest(home, entries)
            return result
        finally:
            if temp.exists():
                temp.unlink()
