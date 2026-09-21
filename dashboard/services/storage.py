import os
import shutil
from seed.paths import checked_path


class StorageService:
    def __init__(self, home):
        self.home = home

    def inventory(self, budget=2 * 1024**3):
        totals = dict(database_bytes=0, logs_bytes=0, backups_bytes=0, other_bytes=0)
        if self.home.exists():
            checked_path(self.home, '.')
            for directory, dirs, files in os.walk(self.home, followlinks=False):
                dirs[:] = [d for d in dirs if not (self.home.__class__(directory) / d).is_symlink()]
                for name in files:
                    path = self.home.__class__(directory) / name
                    if path.is_symlink():
                        continue
                    rel = path.relative_to(self.home)
                    if rel.parts[0] in ('app', 'venv'):
                        key = 'other_bytes'
                    elif name.startswith('memory.sqlite3') and len(rel.parts) == 1:
                        key = 'database_bytes'
                    elif rel.parts[0] == 'backups':
                        key = 'backups_bytes'
                    elif '.log' in name:
                        key = 'logs_bytes'
                    elif name.endswith('.lock'):
                        continue
                    else:
                        key = 'other_bytes'
                    try:
                        totals[key] += path.stat().st_size
                    except FileNotFoundError:
                        continue
        totals['total_bytes'] = sum(totals.values())
        totals['budget_bytes'] = budget
        totals['percent_used'] = round(totals['database_bytes'] / budget * 100, 2)
        totals['recommendation'] = 'Storage review recommended; checkpointing preserves all memories.' if totals['percent_used'] >= 80 else None
        totals['logical_table_bytes'] = None
        try:
            disk = shutil.disk_usage(self.home if self.home.exists() else self.home.parent)
            totals['disk_free_bytes'] = disk.free
        except OSError:
            totals['disk_free_bytes'] = None
        return totals
