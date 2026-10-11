"""Declared producer-fixture setup only, before immutable selection assays."""
import hashlib
import json
import threading
import time

from .contracts import ContractError
from .registry import ACTIONS
from .state import OwnedState, _worker_only


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def admit_c_workspace(snapshot_bytes, *, generating_bytes):
    values = tuple(snapshot_bytes)
    if (len(values) != 4 or any(type(n) is not int or not 0 <= n <= 32*1024**2 for n in values)
            or type(generating_bytes) is not int or not 0 <= generating_bytes <= 32*1024**2
            or sum(values) + generating_bytes > 128*1024**2):
        raise ContractError()


def build_fixture(fixture_id: str, owned: OwnedState) -> OwnedState:
    _worker_only()
    if (type(owned) is not OwnedState or owned._closed or owned.monitor.stopped
            or fixture_id not in ('cold', 'conflict', 'unavailable', 'stale')):
        raise ContractError()
    db, memory = owned.memory.db, owned.memory
    count = db.execute('SELECT COUNT(*) FROM transitions').fetchone()[0]
    if db.in_transaction or (fixture_id in ('cold', 'conflict') and count != 0) or (fixture_id in ('unavailable', 'stale') and count != 128):
        raise ContractError()
    before = _digest(owned.raw_tables())
    source_id = None
    modification = None
    reason = 'registered_producer_fixture_setup'
    if fixture_id == 'conflict':
        from seed.world_model import WorldModel
        from seed.semantic_memory import Consolidator
        from seed.self_model import SelfModel
        base = time.time()
        public = dict(battery_pct=80, charging=False, load_ratio=.5, disk_free_pct=50, network=False, local_hour=12)
        model = WorldModel(memory)
        for ordinal in range(1, 129):
            action = ACTIONS[(ordinal-1) % 4]
            before_state = dict(public, wall_time=base+ordinal-1)
            outcome = dict(public, wall_time=base+ordinal, load_ratio=.6 if ordinal <= 64 else .4)
            _, tid = memory.record_transition_experience(state_before=before_state, action=action,
                state_after=outcome, outcome={'status': 'completed'}, legacy_reward=0.,
                started_at=base+ordinal-1, completed_at=base+ordinal,
                note='producer_fixture_v1', world_model_eligible=True)
            if not model.observe_transition(tid):
                raise ContractError()
        last = base + 128
        result = Consolidator(memory, clock=lambda: last).run(public, provenance='owner_requested')
        if result['status'] != 'completed':
            raise ContractError()
        if SelfModel(memory, clock=lambda: last).update(tid, 'producer_fixture_v1', threading.Event()) != 'updated':
            raise ContractError()
    elif fixture_id == 'unavailable':
        from seed.semantic_memory import Consolidator
        candidate = db.execute('SELECT source_belief_id FROM semantic_memories ORDER BY id LIMIT 1').fetchone()
        if candidate is None:
            raise ContractError()
        source_id = candidate[0]
        old = db.execute('SELECT value_json FROM world_beliefs WHERE id=?', (source_id,)).fetchone()[0]
        invalid = '{"declared_invalid_fixture_payload":true}'
        modification = _digest({'source_id': source_id, 'before_payload': old, 'after_payload': invalid})
        with db:
            db.execute('UPDATE world_beliefs SET value_json=? WHERE id=?', (invalid, source_id))
        # Same source row survives; the real producer owns the unavailable status.
        result = Consolidator(memory).run(dict(battery_pct=80, charging=False, load_ratio=.5, disk_free_pct=50), provenance='owner_requested')
        status = db.execute('SELECT status FROM semantic_memories WHERE source_belief_id=?', (source_id,)).fetchone()
        if status is None or status[0] != 'source_unavailable' or result['failed_count'] < 1:
            raise ContractError()
        reason = 'declared_invalid_typed_source_payload'
    last = db.execute('SELECT MAX(completed_at) FROM transitions').fetchone()[0]
    last = time.time() if last is None else last
    owned.fixture_provenance = dict(fixture_id=fixture_id, fixture_version=1,
        driver='producer_fixture_v1', source_identity=source_id,
        modification_digest=modification, reason=reason, timing='initial_state_setup',
        before_freeze=True, initial_digest=before, final_digest=_digest(owned.raw_tables()),
        last_evidence_time=last, read_time=last+301 if fixture_id == 'stale' else last,
        transition_ids=[row[0] for row in db.execute('SELECT id FROM transitions ORDER BY id')])
    return owned
