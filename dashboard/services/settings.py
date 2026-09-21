import json
from seed.config import DEFAULTS, validate_settings
from seed.telemetry import audit, emit
from .read_store import ReadStore, ServiceError, decode


class SettingsStore:
    def __init__(self, home):
        self.store = ReadStore(home)

    def get(self):
        with self.store.connection() as db:
            tables = self.store.tables(db)
            row = db.execute('SELECT revision,data_json FROM settings WHERE singleton=1').fetchone() if 'settings' in tables else None
            values = {**DEFAULTS, **(decode(row[1], {}) if row else {})}
            runtime = db.execute('SELECT data_json FROM runtime WHERE singleton=1').fetchone() if 'runtime' in tables else None
            rt = decode(runtime[0], {}) if runtime else {}
            return {'revision':row[0] if row else 0, 'values':values, 'effective':rt.get('effective_settings'),
                    'applied_revision':rt.get('settings_revision'), 'available':'settings' in tables,
                    'backup_directory':'backups (inside SEED home)', 'port_requires_restart':True,
                    'experimental_supported':False}

    def update(self, data, revision):
        try:
            patch = validate_settings(data)
        except ValueError as error:
            raise ServiceError('invalid_settings', str(error)) from error
        if type(revision) is not int or revision < 0:
            raise ServiceError('invalid_revision','Invalid settings revision.')
        with self.store.connection(write=True) as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT revision,data_json FROM settings WHERE singleton=1').fetchone()
            if (row[0] if row else 0) != revision:
                raise ServiceError('revision_conflict','Settings changed elsewhere. Refresh before saving.',409)
            old = {**DEFAULTS, **(decode(row[1], {}) if row else {})}
            values = {**old, **patch}
            db.execute('INSERT INTO settings VALUES(1,?,?) ON CONFLICT(singleton) DO UPDATE SET revision=excluded.revision,data_json=excluded.data_json',
                       (revision+1,json.dumps(values,allow_nan=False)))
            changes = {k:{'old':old[k],'new':v} for k,v in patch.items() if old[k] != v}
            audit(db,'settings_changed',changes,{'revision':revision+1})
            emit(db,'OWNER','settings','Owner changed settings',{'changes':changes,'revision':revision+1})
        return self.get()
