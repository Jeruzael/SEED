import re
from seed.backup import create_backup, read_manifest, write_manifest
from seed.runtime import InstanceLock
from seed.paths import checked_path
from seed.telemetry import emit, audit
from .read_store import ReadStore


class BackupStore:
    def __init__(self, home):
        self.home = home
        self.store = ReadStore(home)

    def create(self):
        result = create_backup(self.home)
        with self.store.connection(write=True) as db:
            emit(db, 'SYSTEM', 'backup', 'Verified SQLite backup created', result)
            audit(db, 'backup_created', {}, result)
        return result

    def prune(self, retention):
        if type(retention) is not int or not 1 <= retention <= 100:
            raise ValueError('Retention must be 1–100 backups')
        removed = []
        with InstanceLock(checked_path(self.home, 'backup.lock')):
            entries = read_manifest(self.home)
            survivors = list(entries)
            for entry in entries[:-retention]:
                name = entry.get('name','')
                if not re.fullmatch(r'memory-\d{8}-\d{6}-[0-9a-f]{12}\.sqlite3',name):
                    continue
                path = checked_path(self.home, 'backups/' + name)
                if path.is_file() and path.stat().st_size == entry.get('bytes'):
                    path.unlink()
                    removed.append(name)
                    survivors.remove(entry)
            write_manifest(self.home, survivors)
        return {'removed':removed}
