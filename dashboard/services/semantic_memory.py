"""Bounded, read-only inspection of current semantic knowledge and prior revisions."""
from seed.semantic_memory import normalized_source
from seed.world_model import SIGNALS
from .read_store import ServiceError, decode

MAX_ID = 2**63-1


def bounds(cursor, limit):
    if type(cursor) is not int or not 0 <= cursor <= MAX_ID or type(limit) is not int or not 1 <= limit <= 100:
        raise ServiceError('invalid_query', 'Invalid semantic pagination.')


def identity(semantic_id):
    if type(semantic_id) is not int or not 1 <= semantic_id <= MAX_ID:
        raise ServiceError('invalid_id', 'Invalid semantic memory ID.')


def record(row):
    item = dict(row)
    item['payload'] = decode(item.pop('payload_json'), {})
    return item


class SemanticReadService:
    def __init__(self, store):
        self.store = store

    @staticmethod
    def current(db, row):
        item = record(row)
        source = db.execute('SELECT * FROM world_beliefs WHERE id=?', (item['source_belief_id'],)).fetchone()
        try:
            if source is None:
                raise ValueError('Missing source')
            normalized_source(source)
            item['source_status'] = 'available'
        except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
            item['source_status'] = 'source_unavailable'
        return item

    def memories(self, signal=None, scope=None, status=None, after=0, limit=50):
        bounds(after, limit)
        if (signal not in (None, *SIGNALS) or scope not in (None, 'global', 'action') or
            status not in (None, 'active', 'weakened', 'source_unavailable')):
            raise ServiceError('invalid_query', 'Invalid semantic filter.')
        with self.store.connection() as db:
            if 'semantic_memories' not in self.store.tables(db):
                return dict(available=False, items=[], next_cursor=None)
            rows = db.execute('''SELECT * FROM semantic_memories WHERE id>?
                AND (? IS NULL OR signal=?) AND (? IS NULL OR scope=?) AND (? IS NULL OR status=?)
                ORDER BY id LIMIT ?''', (after,signal,signal,scope,scope,status,status,limit+1)).fetchall()
            return dict(available=True, items=[self.current(db,r) for r in rows[:limit]],
                        next_cursor=rows[limit-1]['id'] if len(rows)>limit else None)

    def _row(self, db, semantic_id):
        row = db.execute('SELECT * FROM semantic_memories WHERE id=?', (semantic_id,)).fetchone() \
            if 'semantic_memories' in self.store.tables(db) else None
        if row is None:
            raise ServiceError('not_found', 'Semantic memory does not exist.', 404)
        return row

    def memory(self, semantic_id):
        identity(semantic_id)
        with self.store.connection() as db:
            return self.current(db, self._row(db, semantic_id))

    def history(self, semantic_id, before=MAX_ID, limit=50):
        identity(semantic_id)
        bounds(before, limit)
        with self.store.connection() as db:
            self._row(db, semantic_id)
            rows = db.execute('''SELECT * FROM semantic_memory_history
                WHERE semantic_memory_id=? AND revision<=? ORDER BY revision DESC LIMIT ?''',
                (semantic_id,before,limit+1)).fetchall()
            items = []
            for row in rows[:limit]:
                item = dict(row)
                snapshot = decode(item.pop('record_json'), {})
                item['record'] = record(snapshot) if 'payload_json' in snapshot else snapshot
                items.append(item)
            return dict(available=True,items=items,
                        next_cursor=rows[limit-1]['revision']-1 if len(rows)>limit else None)

    def runs(self, before=MAX_ID, limit=50):
        bounds(before, limit)
        with self.store.connection() as db:
            if 'consolidation_runs' not in self.store.tables(db):
                return dict(available=False, items=[], next_cursor=None)
            rows = db.execute('SELECT * FROM consolidation_runs WHERE id<=? ORDER BY id DESC LIMIT ?',
                              (before,limit+1)).fetchall()
            items = []
            for row in rows[:limit]:
                item = dict(row)
                item['result'] = decode(item.pop('result_json'), {})
                items.append(item)
            return dict(available=True,items=items,
                        next_cursor=rows[limit-1]['id']-1 if len(rows)>limit else None)
