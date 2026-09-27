"""Read one stored B7 snapshot; never construct core memory or inspect processes."""
import json
import time
from seed.self_model import decode_snapshot, project_snapshot, sql_budget, number
from .read_store import ServiceError


class SelfModelReadService:
    def __init__(self, store, clock=time.time):
        self.store, self.clock = store, clock

    def get(self):
        now = self.clock()
        if not number(now):
            raise ServiceError('invalid_clock', 'Inspection time is unavailable.', 503)
        def absent(status, reason):
            return dict(available=False, status=status, reason=reason, read_at=now, snapshot=None)
        with self.store.connection() as db:
            db.execute('PRAGMA busy_timeout=0')
            with sql_budget(db):
                db.execute('BEGIN')
                tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('seed_schema','self_model_current') LIMIT 2")}
                if 'seed_schema' not in tables:
                    return absent('unavailable', 'legacy_schema')
                versions = db.execute('SELECT version FROM seed_schema LIMIT 2').fetchall()
                if len(versions) != 1 or type(versions[0][0]) is not int or not 1 <= versions[0][0] <= 7:
                    raise ServiceError('incompatible_schema', 'Self model cannot use this schema version.', 409)
                if versions[0][0] < 6:
                    return absent('unavailable', 'legacy_schema')
                if 'self_model_current' not in tables:
                    return absent('error', 'invalid_snapshot')
                row = db.execute('''SELECT updated_at,model,model_version,source_transition_id,
                    substr(CAST(data_json AS BLOB),1,32769) AS data FROM self_model_current WHERE singleton=1''').fetchone()
                if row is None:
                    return absent('unavailable', 'awaiting_first_cycle')
                try:
                    p = decode_snapshot(row['data'])
                    if (row['updated_at'] != p['measured_at'] or row['model'] != p['model'] or
                        type(row['model_version']) is not int or row['model_version'] != p['model_version'] or
                        type(row['source_transition_id']) is not int or row['source_transition_id'] != p['source_transition_id']):
                        raise ValueError('invalid_snapshot')
                    if db.execute('SELECT id FROM transitions WHERE id=?', (p['source_transition_id'],)).fetchone() is None:
                        raise ValueError('invalid_snapshot')
                    result = dict(available=True, status='stored', reason=None, read_at=now, snapshot=project_snapshot(p, now))
                    if len(json.dumps(result, ensure_ascii=True, allow_nan=False).encode()) > 40960:
                        raise ValueError('invalid_snapshot')
                    return result
                except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
                    return absent('error', 'invalid_snapshot')
