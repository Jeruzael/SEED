"""The dashboard's narrow, read-only view of SEED; no organism is constructed."""
from __future__ import annotations
import copy
from collections import Counter
import math
import threading
import time
from pathlib import Path
from seed.runtime import owner
from seed.world_model import SIGNALS, ACTIONS
from .read_store import ReadStore, ServiceError, decode
from .process import ProcessController
from .storage import StorageService
from .semantic_memory import SemanticReadService
from .self_model import SelfModelReadService


class SeedService:
    def __init__(self, home: Path, process=None, clock=time.time):
        self.home = Path(home).absolute()
        self.store = ReadStore(self.home)
        self.process = process or ProcessController(self.home)
        self.clock = clock
        self._cache = {}
        self._lock = threading.RLock()

    def cached(self, key, seconds, fn):
        with self._lock:
            now = self.clock()
            saved = self._cache.get(key)
            if not saved or not 0 <= now - saved[0] < seconds:
                saved = (now, fn())
                self._cache[key] = saved
            return copy.deepcopy(saved[1])

    def invalidate(self):
        with self._lock:
            self._cache.clear()

    @staticmethod
    def meta(db):
        return {r['key']: decode(r['value']) for r in db.execute('SELECT * FROM meta')}

    @staticmethod
    def runtime(db, tables):
        row = db.execute('SELECT data_json FROM runtime WHERE singleton=1').fetchone() if 'runtime' in tables else None
        value = decode(row[0], {}) if row else {}
        return value if isinstance(value, dict) else {}

    def status(self):
        def read():
            process = self.process.status()
            try:
                with self.store.connection() as db:
                    tables = self.store.tables(db)
                    meta = self.meta(db)
                    runtime = self.runtime(db, tables)
                    counts = self.cached('counts', 10, lambda: {t: db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ('episodes', 'concepts')})
                identity = meta.get('identity') or {}
                now = self.clock()
                heartbeat = runtime.get('heartbeat')
                age = now - heartbeat if isinstance(heartbeat, (int, float)) else None
                ownership = owner(self.home / 'organism.lock')
                owns = bool(ownership and ownership.get('session_id') == runtime.get('session_id') and ownership.get('pid') == runtime.get('pid'))
                fresh = owns and age is not None and 0 <= age <= 10
                lifecycle = runtime.get('lifecycle') if fresh else None
                reason = None if fresh else 'Current activity is unverified; telemetry is missing or stale.'
                if not owns and runtime.get('lifecycle') in ('STOPPED', 'ERROR'):
                    lifecycle = runtime['lifecycle']
                    reason = 'Last recorded process state; no active core lock.'
                elif not owns and process['state'] in ('unregistered', 'loaded'):
                    lifecycle = 'STOPPED'
                    reason = 'LaunchAgent is not running; no active core lock.'
                return {'data_state': 'ready', 'compatibility': 'instrumented' if 'runtime' in tables else 'legacy',
                        'identity': identity, 'lifecycle': lifecycle, 'fresh': fresh, 'freshness_seconds': age,
                        'reason': reason, 'runtime': runtime, 'process': process, **counts,
                        'last_wake': meta.get('last_wake'), 'last_sleep': meta.get('last_sleep'),
                        'last_action': meta.get('last_action'), 'last_state': meta.get('last_state'),
                        'development_age_seconds': max(0, now - identity['born_at']) if isinstance(identity.get('born_at'), (int,float)) else None,
                        'uptime_seconds': max(0, now - runtime['started_at']) if fresh and runtime.get('started_at') else None}
            except (ServiceError, ValueError, OSError) as error:
                return {'data_state': 'missing' if isinstance(error, ServiceError) and error.code == 'missing_database' else 'error',
                        'compatibility': 'unavailable', 'lifecycle': None, 'fresh': False,
                        'reason': str(error), 'process': process, 'runtime': {}, 'identity': {}}
        return self.cached('status', 2, read)

    def environment(self):
        with self.store.connection() as db:
            state = self.meta(db).get('last_state')
            state = state if isinstance(state, dict) else {}
            timestamp = state.get('wall_time')
            return {'state': state, 'age_seconds': max(0, self.clock() - timestamp) if isinstance(timestamp,(int,float)) else None}

    def memories(self, search='', event=None, sort='newest', page=1, page_size=50):
        sorts = {'newest': 'e.id DESC', 'oldest': 'e.id ASC', 'reward': 'e.reward DESC,e.id DESC'}
        if sort not in sorts or not 1 <= page_size <= 100 or not 1 <= page <= 100000 or len(search) > 200:
            raise ServiceError('invalid_query', 'Invalid pagination, search, or sort.')
        with self.store.connection() as db:
            where = "(?='' OR e.note LIKE ? OR e.event LIKE ? OR e.action LIKE ? OR e.state_json LIKE ?) AND (? IS NULL OR e.event=?)"
            args = (search, *(['%' + search + '%'] * 4), event, event)
            count = db.execute('SELECT COUNT(*) FROM episodes e WHERE ' + where, args).fetchone()[0]
            rows = db.execute('SELECT e.* FROM episodes e WHERE ' + where + ' ORDER BY ' + sorts[sort] + ' LIMIT ? OFFSET ?',
                              (*args, page_size, (page-1)*page_size)).fetchall()
            tables = self.store.tables(db)
            items = [self._episode(db, row, tables) for row in rows]
        return {'items': items, 'total': count, 'page': page, 'page_size': page_size}

    @staticmethod
    def _episode(db, row, tables):
        item = dict(row)
        state = decode(item.pop('state_json'), None)
        item['warning'] = None if isinstance(state, dict) else 'Stored state JSON is invalid.'
        item['state'] = state if isinstance(state, dict) else {}
        annotation = db.execute('SELECT important,tags_json FROM annotations WHERE episode_id=?', (item['id'],)).fetchone() if 'annotations' in tables else None
        item['important'] = bool(annotation[0]) if annotation else False
        item['tags'] = decode(annotation[1], []) if annotation else []
        return item

    def memory(self, episode_id):
        with self.store.connection() as db:
            row = db.execute('SELECT * FROM episodes WHERE id=?', (episode_id,)).fetchone()
            if not row:
                raise ServiceError('not_found', 'Episode does not exist.', 404)
            return self._episode(db, row, self.store.tables(db))

    def concepts(self):
        with self.store.connection() as db:
            tables = self.store.tables(db)
            items = []
            for row in db.execute('SELECT * FROM concepts ORDER BY updated_at DESC'):
                item = dict(row)
                item['payload'] = decode(item.pop('payload_json'), {})
                ev = db.execute('SELECT * FROM concept_evidence WHERE name=?', (item['name'],)).fetchone() if 'concept_evidence' in tables else None
                item.update(created_at=ev['created_at'] if ev else None,
                            episode_ids=decode(ev['episode_ids_json'], []) if ev else [],
                            provenance='Recorded sample IDs' if ev else 'Legacy sample IDs unavailable',
                            evidence_scope='Qualifying samples in the latest reflection window, not lifetime observations')
                items.append(item)
        return {'items': items}

    @staticmethod
    def _world_belief(row):
        item = dict(row)
        item['value'] = decode(item.pop('value_json'), {})
        item['confidence_kind'] = 'evidence_consistency'
        return item

    def world_beliefs(self, signal=None, scope=None, scope_value=None, after=0, limit=50):
        """Bounded keyset inspection, with no construction/migration of core memory."""
        if (type(limit) is not int or not 1 <= limit <= 100 or
            type(after) is not int or not 0 <= after <= 2**63-1 or
            signal not in (None, *SIGNALS) or scope not in (None, 'global', 'action') or
            scope_value not in (None, '', *ACTIONS)):
            raise ServiceError('invalid_query', 'Invalid world-belief filter or pagination.')
        with self.store.connection() as db:
            if 'world_beliefs' not in self.store.tables(db):
                return {'available': False, 'items': [], 'next_cursor': None}
            rows = db.execute('''SELECT * FROM world_beliefs WHERE id>?
                AND (? IS NULL OR signal=?) AND (? IS NULL OR scope=?)
                AND (? IS NULL OR scope_value=?) ORDER BY id LIMIT ?''',
                (after,signal,signal,scope,scope,scope_value,scope_value,limit+1)).fetchall()
            return {'available': True, 'items': [self._world_belief(r) for r in rows[:limit]],
                    'next_cursor': rows[limit-1]['id'] if len(rows)>limit else None}

    def world_belief(self, belief_id):
        if type(belief_id) is not int or not 1 <= belief_id <= 2**63-1:
            raise ServiceError('invalid_id', 'Invalid world-belief ID.')
        with self.store.connection() as db:
            row = db.execute('SELECT * FROM world_beliefs WHERE id=?', (belief_id,)).fetchone() \
                if 'world_beliefs' in self.store.tables(db) else None
            if row is None:
                raise ServiceError('not_found', 'World belief does not exist.', 404)
            return self._world_belief(row)

    @staticmethod
    def _curiosity(row):
        item = dict(row)
        item['components'] = decode(item.pop('components_json'), {})
        return item

    def curiosity_assessments(self, before=2**63-1, limit=50):
        if (type(before) is not int or not 0 <= before <= 2**63-1 or
            type(limit) is not int or not 1 <= limit <= 100):
            raise ServiceError('invalid_query', 'Invalid curiosity pagination.')
        with self.store.connection() as db:
            if 'curiosity_assessments' not in self.store.tables(db):
                return {'available': False, 'items': [], 'next_cursor': None}
            rows = db.execute('SELECT * FROM curiosity_assessments WHERE transition_id<=? '
                              'ORDER BY transition_id DESC LIMIT ?', (before,limit+1)).fetchall()
            return {'available': True, 'items': [self._curiosity(r) for r in rows[:limit]],
                    'next_cursor': rows[limit-1]['transition_id']-1 if len(rows)>limit else None}

    def curiosity_assessment(self, transition_id):
        if type(transition_id) is not int or not 1 <= transition_id <= 2**63-1:
            raise ServiceError('invalid_id', 'Invalid curiosity transition ID.')
        with self.store.connection() as db:
            row = db.execute('SELECT * FROM curiosity_assessments WHERE transition_id=?', (transition_id,)).fetchone() \
                if 'curiosity_assessments' in self.store.tables(db) else None
            if row is None:
                raise ServiceError('not_found', 'Curiosity assessment does not exist.', 404)
            return self._curiosity(row)

    def curiosity_summary(self):
        with self.store.connection() as db:
            available = 'curiosity_assessments' in self.store.tables(db)
            rows = db.execute('SELECT * FROM curiosity_assessments ORDER BY transition_id DESC LIMIT 100').fetchall() \
                if available else []
        def mean(key):
            values = [r[key] for r in rows if r['status']=='evaluated' and
                      type(r[key]) in (int,float) and math.isfinite(r[key])]
            return math.fsum(values)/len(values) if values else None
        return dict(available=available, window_limit=100, assessment_count=len(rows),
                    mean_score=mean('score'), mean_prediction_surprise=mean('prediction_surprise'),
                    mean_uncertainty=mean('uncertainty'), mean_novelty=mean('novelty'),
                    counts_by_level=dict(Counter(r['level'] for r in rows)),
                    eligible_reflection_count=sum(r['reflection_eligible'] for r in rows),
                    claimed_reflection_count=sum(r['reflection_claimed'] for r in rows),
                    completed_reflection_count=sum(r['reflection_completed'] for r in rows),
                    suppressed_reflection_count=sum(r['suppression_reason'] is not None for r in rows),
                    suppression_reasons=dict(Counter(r['suppression_reason'] for r in rows if r['suppression_reason'])),
                    failure_count=sum(r['failure_reason'] is not None for r in rows))

    def decisions(self, before=None, limit=20):
        from .decisions import DecisionReadService
        return DecisionReadService(self.store).list(before, limit)

    def decision(self, transition_id):
        from .decisions import DecisionReadService
        return DecisionReadService(self.store).detail(transition_id)

    def self_model(self):
        return SelfModelReadService(self.store, self.clock).get()

    def semantic_memories(self, signal=None, scope=None, status=None, after=0, limit=50):
        return SemanticReadService(self.store).memories(signal, scope, status, after, limit)

    def semantic_memory(self, semantic_id):
        return SemanticReadService(self.store).memory(semantic_id)

    def semantic_history(self, semantic_id, before=2**63-1, limit=50):
        return SemanticReadService(self.store).history(semantic_id, before, limit)

    def consolidation_runs(self, before=2**63-1, limit=50):
        return SemanticReadService(self.store).runs(before, limit)

    def learning(self):
        with self.store.connection() as db:
            rt = self.runtime(db, self.store.tables(db))
            rows = [dict(row) for row in db.execute('SELECT * FROM q_values ORDER BY state_key,action')]
            recent = [dict(r) for r in db.execute('SELECT ts,action,reward FROM episodes WHERE reward IS NOT NULL ORDER BY id DESC LIMIT 50')]
            distribution = [dict(r) for r in db.execute("SELECT action,COUNT(*) AS count FROM episodes WHERE event='experience' GROUP BY action")]
            return {'values': rows, 'last_decision': rt.get('last_decision'), 'epsilon': rt.get('epsilon'),
                    'alpha': rt.get('alpha'), 'known_states': len({r['state_key'] for r in rows}),
                    'actions': ['observe','reflect','consolidate','rest'], 'recent_rewards': recent, 'distribution': distribution}

    def events(self, after=0, limit=100):
        if not 0 <= after <= 2**63-1 or not 1 <= limit <= 100:
            raise ServiceError('invalid_cursor', 'Invalid event cursor or limit.')
        with self.store.connection() as db:
            if 'events' not in self.store.tables(db):
                return {'items': [], 'legacy': True, 'gap': False, 'reset': False, 'latest_id': 0}
            low, high = db.execute('SELECT MIN(id),MAX(id) FROM events').fetchone()
            reset = after > (high or 0)
            gap = bool(after and low and after < low-1)
            cursor = 0 if reset else after
            rows = db.execute('SELECT * FROM events WHERE id>? ORDER BY id LIMIT ?', (cursor, limit)).fetchall()
            items = []
            for row in rows:
                item = dict(row)
                item['data'] = decode(item.pop('data_json'), {})
                items.append(item)
            return {'items': items, 'legacy': False, 'gap': gap, 'reset': reset, 'latest_id': high or 0}

    def history(self, limit=200):
        if not 2 <= limit <= 500:
            raise ServiceError('invalid_query', 'History limit must be 2–500.')
        def read():
            with self.store.connection() as db:
                rows = db.execute("SELECT id,ts,event,state_json FROM episodes WHERE event IN ('experience','wake','sleep') ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
                return {'items': [{'id':r['id'], 'ts':r['ts'], 'event':r['event'], 'state':decode(r['state_json'],{})} for r in reversed(rows)]}
        return self.cached(('history', limit), 30, read)

    def development(self):
        with self.store.connection() as db:
            counts = {r[0]:r[1] for r in db.execute('SELECT event,COUNT(*) FROM episodes GROUP BY event')}
            timeline = [dict(r) for r in db.execute("SELECT ts,event,note FROM episodes WHERE event IN ('wake','sleep') ORDER BY id DESC LIMIT 20")]
            return {'observations': counts.get('experience',0), 'owner_interactions': counts.get('owner',0),
                    'wake_records': counts.get('wake',0), 'sleep_stop_records': counts.get('sleep',0),
                    'known_contexts': db.execute('SELECT COUNT(DISTINCT state_key) FROM q_values').fetchone()[0],
                    'learning_updates': db.execute('SELECT COALESCE(SUM(visits),0) FROM q_values').fetchone()[0],
                    'concepts': db.execute('SELECT COUNT(*) FROM concepts').fetchone()[0],
                    'timeline': timeline, 'scope': 'Counts from retained records; wake gaps are inferred, sleep includes process stop.'}

    def storage(self):
        def read():
            budget = 2*1024**3
            try:
                with self.store.connection() as db:
                    if 'settings' in self.store.tables(db):
                        row = db.execute('SELECT data_json FROM settings WHERE singleton=1').fetchone()
                        settings = decode(row[0], {}) if row else {}
                        budget = settings.get('memory_budget', budget)
            except ServiceError:
                pass
            return StorageService(self.home).inventory(budget)
        return self.cached('storage', 5, read)

    def health(self):
        status = self.status()
        errors = []
        try:
            with self.store.connection() as db:
                if 'events' in self.store.tables(db):
                    errors = [dict(r) for r in db.execute("SELECT ts,message,data_json FROM events WHERE category='ERROR' ORDER BY id DESC LIMIT 20")]
                    count = db.execute("SELECT COUNT(*) FROM events WHERE category='ERROR'").fetchone()[0]
                else:
                    count = None
            database = 'readable'
        except ServiceError:
            database, count = 'unavailable', None
        return {'database':database, 'last_error': status['runtime'].get('last_error'), 'errors': errors,
                'error_count':count, 'last_successful_cycle':status['runtime'].get('last_successful_cycle'),
                'process':status['process'], 'fresh':status['fresh']}
