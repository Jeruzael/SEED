"""Persistent descriptive transition statistics; no predictor or policy feedback."""
import json
import math
import time
from .telemetry import emit

MODEL_VERSION = 1
RECOVERY_LIMIT = 100
ACTIONS = ('observe', 'reflect', 'consolidate', 'rest')
DELTA_EPSILON = {'battery_pct': .05, 'load_ratio': .02, 'disk_free_pct': .01}
SIGNALS = (*DELTA_EPSILON, 'network_reachable')


def confidence(evidence_count, contradiction_count):
    """Bounded evidence support × observed consistency, not truth probability."""
    if evidence_count <= 0:
        return 0.0
    return max(0.0, min(.95, min(.95, evidence_count / 20) *
                        (1 - contradiction_count / evidence_count)))


def _state(raw):
    # Decode independently: a malformed before-state does not invalidate an
    # otherwise valid after-state Boolean observation. Bad fields stay unavailable.
    if not isinstance(raw, str) or len(raw) > 16384:
        return {}
    try:
        value = json.loads(raw, parse_constant=lambda _: None)
    except (ValueError, TypeError, RecursionError):
        return {}
    return value if isinstance(value, dict) else {}


def _number(value, signal):
    if type(value) not in (int, float):
        return None
    try:
        value = float(value)
    except (OverflowError, ValueError):
        return None
    if not math.isfinite(value) or value < 0:
        return None
    if signal != 'load_ratio' and value > 100:
        return None
    return value


def _samples(row):
    if row['action'] not in ACTIONS:
        return {}
    before, after = _state(row['state_before_json']), _state(row['state_after_json'])
    samples = {}
    for signal in DELTA_EPSILON:
        a, b = _number(before.get(signal), signal), _number(after.get(signal), signal)
        if a is not None and b is not None:
            samples[signal] = b - a
    network = after.get('network')  # Existing sensor key; target name differs.
    if type(network) is bool:
        samples['network_reachable'] = network
    return samples


def _mean(old, sample, count):
    # The usual incremental formula is safe for equal signs. Opposite extrema
    # can overflow sample-old, so use a convex weighted sum in that case.
    if (old >= 0) == (sample >= 0):
        return old + (sample - old) / count
    return old * ((count - 1) / count) + sample / count


def _revise(signal, sample, old):
    n = old['evidence_count'] if old else 0
    value = json.loads(old['value_json']) if old else {}
    contradictory = False
    if signal in DELTA_EPSILON:
        mean = value.get('mean_delta', sample)
        epsilon = DELTA_EPSILON[signal]
        contradictory = n >= 4 and ((mean > epsilon and sample < -epsilon) or
                                    (mean < -epsilon and sample > epsilon))
        updated = dict(mean_delta=_mean(mean, sample, n+1),
                       mean_absolute_delta=_mean(value.get('mean_absolute_delta', abs(sample)), abs(sample), n+1),
                       min_delta=min(value.get('min_delta', sample), sample),
                       max_delta=max(value.get('max_delta', sample), sample))
    else:
        probability = value.get('probability_true', .5)
        contradictory = n >= 4 and ((probability >= .75 and not sample) or
                                    (probability <= .25 and sample))
        trues = value.get('true_count', 0) + int(sample)
        updated = dict(true_count=trues, false_count=n+1-trues, probability_true=trues/(n+1))
    updated['confidence_kind'] = 'evidence_consistency'
    contradictions = (old['contradiction_count'] if old else 0) + int(contradictory)
    return updated, n+1, contradictions, contradictory


class WorldModel:
    def __init__(self, memory):
        self.memory = memory

    def recover(self):
        """One bounded FIFO pass over explicit pending B4 evidence; never history."""
        with self.memory._lock:
            ids = [r[0] for r in self.memory.db.execute(
                'SELECT transition_id FROM world_model_queue ORDER BY transition_id LIMIT ?',
                (RECOVERY_LIMIT,))]
        return sum(self.observe_transition(tid) for tid in ids)

    def observe_transition(self, transition_id):
        """Process the oldest eligible persisted transition exactly once.

        A failed update rolls back only model work. The completed experience and
        its queue entry survive for retry. IMMEDIATE serializes multiple writers
        before reading statistics, in addition to the in-process Memory lock.
        """
        db = self.memory.db
        with self.memory._lock:
            db.execute('BEGIN IMMEDIATE')
            try:
                if db.execute('SELECT 1 FROM world_model_processed WHERE transition_id=?',
                              (transition_id,)).fetchone():
                    db.commit()
                    return False
                if not db.execute('SELECT 1 FROM world_model_queue WHERE transition_id=?',
                                  (transition_id,)).fetchone():
                    db.commit()
                    return False
                first = db.execute('SELECT transition_id FROM world_model_queue ORDER BY transition_id LIMIT 1').fetchone()[0]
                if first != transition_id:
                    raise ValueError('World-model evidence must be processed in queue order')
                row = db.execute('SELECT * FROM transitions WHERE id=?', (transition_id,)).fetchone()
                if row is None:
                    raise ValueError('Queued transition is missing')
                samples = _samples(row)
                now = time.time()
                for signal, sample in samples.items():
                    for scope, scope_value in (('global', ''), ('action', row['action'])):
                        self._update(signal, sample, scope, scope_value, transition_id, now)
                db.execute('INSERT INTO world_model_processed VALUES(?,?,?,?)',
                           (transition_id, now, MODEL_VERSION, len(samples)))
                db.execute('DELETE FROM world_model_queue WHERE transition_id=?', (transition_id,))
                db.commit()
                return True
            except BaseException:
                db.rollback()
                raise

    def _update(self, signal, sample, scope, scope_value, transition_id, now):
        db = self.memory.db
        family = 'numeric_delta' if signal in DELTA_EPSILON else 'boolean_frequency'
        key = f'{MODEL_VERSION}:{signal}:{scope}:{scope_value}:{family}'
        published = db.execute('SELECT * FROM world_beliefs WHERE belief_key=?', (key,)).fetchone()
        old = published if published is not None else db.execute(
            'SELECT * FROM world_pending WHERE belief_key=?', (key,)).fetchone()
        value, n, contradictions, contradictory = _revise(signal, sample, old)
        score = confidence(n, contradictions)
        table = 'world_beliefs' if n >= 2 else 'world_pending'
        # Table names are fixed above, never supplied by callers or observations.
        db.execute(f'''INSERT INTO {table}(
            belief_key,signal,scope,scope_value,belief_type,value_json,evidence_count,
            contradiction_count,confidence,created_at,updated_at,
            source_first_transition_id,source_last_transition_id,model_version)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(belief_key) DO UPDATE SET
            value_json=excluded.value_json,evidence_count=excluded.evidence_count,
            contradiction_count=excluded.contradiction_count,confidence=excluded.confidence,
            updated_at=excluded.updated_at,source_last_transition_id=excluded.source_last_transition_id''',
            (key,signal,scope,scope_value,family,json.dumps(value,allow_nan=False,sort_keys=True),
             n,contradictions,score,old['created_at'] if old else now,now,
             old['source_first_transition_id'] if old else transition_id,transition_id,MODEL_VERSION))
        if n < 2:
            return
        db.execute('DELETE FROM world_pending WHERE belief_key=?', (key,))
        old_value = json.loads(published['value_json']) if published else None
        # Evidence count/timestamp alone is not material once confidence is capped.
        if not published or contradictory or old_value != value or published['confidence'] != score:
            emit(db, 'WORLD_MODEL', 'world_model', 'Updated descriptive transition statistics',
                 dict(belief_key=key,signal=signal,scope=scope,scope_value=scope_value,
                      change='created' if not published else ('contradicted' if contradictory else 'updated'),
                      old_value=old_value,new_value=value,evidence_count=n,contradiction_count=contradictions,
                      old_confidence=published['confidence'] if published else None,new_confidence=score,
                      transition_id=transition_id))
