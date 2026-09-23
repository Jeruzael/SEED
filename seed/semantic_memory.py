"""Bounded downstream consolidation of descriptive B4 statistics, without forgetting."""
import hashlib
import json
import math
import time
from .world_model import ACTIONS, SIGNALS, _number
from .telemetry import emit

MODEL = 'semantic_v1'
MODEL_VERSION = 1
RUN_LIMIT = 100
MIN_EVIDENCE = 8
MIN_CONFIDENCE = .30
COUNT_FIELDS = ('source_beliefs_examined','eligible_beliefs','created_count','revised_count',
                'weakened_count','unchanged_count','failed_count')


def resource_suppression(state):
    state = state if isinstance(state, dict) else {}
    load = _number(state.get('load_ratio'), 'load_ratio')
    battery = _number(state.get('battery_pct'), 'battery_pct')
    disk = _number(state.get('disk_free_pct'), 'disk_free_pct')
    if load is not None and load > .8:
        return 'high_load'
    if battery is not None and battery < 20 and state.get('charging') is False:
        return 'low_battery'
    if disk is not None and disk < 10:
        return 'low_disk'
    return None


def _finite(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Expected a finite numeric statistic')
    return value


def _canonical(value):
    """JSON numeric equality ignores representational differences such as 1.0."""
    if isinstance(value, dict):
        return {key: _canonical(item) for key,item in value.items()}
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if type(value) is float and math.isfinite(value) and value.is_integer():
        return int(value)
    return value


def normalized_source(row):
    """Validate only the published abstraction; never rediscover raw evidence."""
    signal, scope, scope_value = row['signal'], row['scope'], row['scope_value']
    family = 'boolean_frequency' if signal=='network_reachable' else 'numeric_delta'
    if (signal not in SIGNALS or row['belief_type'] != family or row['model_version'] != 1 or
        not ((scope=='global' and scope_value=='') or (scope=='action' and scope_value in ACTIONS)) or
        row['belief_key'] != f'1:{signal}:{scope}:{scope_value}:{family}'):
        raise ValueError('Unsupported world-belief identity')
    n, contradictions, confidence = row['evidence_count'], row['contradiction_count'], row['confidence']
    if type(n) is not int or n < 2 or type(contradictions) is not int or not 0 <= contradictions <= n:
        raise ValueError('Invalid evidence counts')
    if not 0 <= _finite(confidence) <= .95:
        raise ValueError('Invalid source confidence')
    _finite(row['updated_at'])
    for key in ('source_first_transition_id','source_last_transition_id'):
        if type(row[key]) is not int or row[key] < 1:
            raise ValueError('Invalid source transition provenance')
    raw = row['value_json']
    if not isinstance(raw, str) or len(raw) > 16384:
        raise ValueError('Invalid source payload size')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('Expected structured source statistics')
    if family == 'numeric_delta':
        payload = {key: _finite(value[key]) for key in ('mean_delta','mean_absolute_delta','min_delta','max_delta')}
        if not payload['min_delta'] <= payload['mean_delta'] <= payload['max_delta'] or payload['mean_absolute_delta'] < 0:
            raise ValueError('Inconsistent numeric statistics')
        if signal != 'load_ratio' and any(abs(v)>100 for v in payload.values()):
            raise ValueError('Numeric delta outside observed percentage domain')
        payload['interpretation'] = 'observed_transition_delta'
    else:
        trues, falses, probability = value['true_count'], value['false_count'], value['probability_true']
        if (type(trues) is not int or type(falses) is not int or min(trues,falses)<0 or trues+falses != n or
            not 0 <= _finite(probability) <= 1 or not math.isclose(probability,trues/n,rel_tol=1e-12,abs_tol=1e-12)):
            raise ValueError('Inconsistent Boolean statistics')
        payload = dict(true_count=trues,false_count=falses,probability_true=probability,
                       interpretation='observed_boolean_frequency')
    semantic_type = family + '_summary'
    data = dict(semantic_key=f'{semantic_type}:{signal}:{scope}:{scope_value}:v{MODEL_VERSION}',
        signal=signal,scope=scope,scope_value=scope_value,semantic_type=semantic_type,
        payload_json=json.dumps(payload,sort_keys=True,allow_nan=False),confidence=confidence,
        evidence_count=n,contradiction_count=contradictions,source_belief_id=row['id'],
        source_belief_model_version=row['model_version'],source_belief_updated_at=row['updated_at'],
        source_first_transition_id=row['source_first_transition_id'],source_last_transition_id=row['source_last_transition_id'])
    # Ignore write-time-only changes but detect changed content at equal/reversed clocks.
    fingerprint = {key: v for key,v in data.items() if key not in ('source_belief_updated_at','payload_json')}
    fingerprint['source_value'] = value
    data['source_fingerprint'] = hashlib.sha256(json.dumps(_canonical(fingerprint),sort_keys=True,allow_nan=False).encode()).hexdigest()
    return data


class Consolidator:
    def __init__(self, memory, clock=None):
        self.memory = memory
        self.clock = clock or time.time

    def _candidates(self):
        db = self.memory.db
        saved = db.execute('SELECT last_belief_id FROM consolidation_state WHERE singleton=1').fetchone()
        cursor = saved[0] if saved else 0
        rows = db.execute('SELECT * FROM world_beliefs WHERE id>? ORDER BY id LIMIT ?', (cursor,RUN_LIMIT)).fetchall()
        if len(rows) < RUN_LIMIT:
            rows += db.execute('SELECT * FROM world_beliefs WHERE id<=? ORDER BY id LIMIT ?',
                               (cursor,RUN_LIMIT-len(rows))).fetchall()
        return rows

    def run(self, state=None, provenance='policy_selected'):
        if provenance not in ('policy_selected','owner_requested'):
            raise ValueError('Unsupported consolidation provenance')
        db = self.memory.db
        reason = resource_suppression(state)
        with self.memory._lock:
            now = self.clock()
            result = dict(reason=reason,examined_ids=[],failures=[])
            with db:
                run_id = db.execute('''INSERT INTO consolidation_runs(
                    started_at,completed_at,model,model_version,provenance,status,result_json)
                    VALUES(?,?,?,?,?,?,?)''', (now,now if reason else None,MODEL,MODEL_VERSION,provenance,
                    'suppressed' if reason else 'running',json.dumps(result,allow_nan=False))).lastrowid
                emit(db,'CONSOLIDATION','semantic_memory','Consolidation suppressed' if reason else 'Consolidation started',
                     dict(run_id=run_id,provenance=provenance,reason=reason))
            if reason is not None:
                return self.get_run(run_id)
            counts = dict.fromkeys(COUNT_FIELDS,0)
            try:
                db.execute('BEGIN IMMEDIATE')
                rows = self._candidates()
                for row in rows:
                    counts['source_beliefs_examined'] += 1
                    result['examined_ids'].append(row['id'])
                    try:
                        data = normalized_source(row)
                    except (ValueError,TypeError,KeyError,OverflowError,RecursionError) as error:
                        counts['failed_count'] += 1
                        result['failures'].append(dict(source_belief_id=row['id'],reason=str(error)[:200]))
                        old = db.execute('SELECT * FROM semantic_memories WHERE source_belief_id=? AND model=? AND model_version=? LIMIT 1',
                                         (row['id'],MODEL,MODEL_VERSION)).fetchone()
                        if old is not None and old['status'] != 'source_unavailable':
                            self._revise(old,dict(status='source_unavailable'),now,run_id)
                            counts['revised_count'] += 1
                        emit(db,'CONSOLIDATION','semantic_memory','Source belief unavailable',
                             dict(run_id=run_id,source_belief_id=row['id'],reason=str(error)[:200]))
                        continue
                    eligible = data['evidence_count'] >= MIN_EVIDENCE and data['confidence'] >= MIN_CONFIDENCE
                    counts['eligible_beliefs'] += int(eligible)
                    old = db.execute('SELECT * FROM semantic_memories WHERE semantic_key=?',(data['semantic_key'],)).fetchone()
                    if old is None:
                        if eligible:
                            data.update(revision=1,status='active',created_at=now,updated_at=now,model=MODEL,model_version=MODEL_VERSION)
                            columns = ','.join(data)
                            sid = db.execute(f'INSERT INTO semantic_memories({columns}) VALUES({",".join("?" for _ in data)})',tuple(data.values())).lastrowid
                            counts['created_count'] += 1
                            emit(db,'SEMANTIC_MEMORY','semantic_memory','Semantic memory consolidated',
                                 dict(run_id=run_id,semantic_memory_id=sid,source_belief_id=row['id'],revision=1,status='active'))
                        else:
                            counts['unchanged_count'] += 1
                        continue
                    status = 'active' if eligible else 'weakened'
                    if old['source_fingerprint']==data['source_fingerprint'] and old['status']==status:
                        counts['unchanged_count'] += 1
                        continue
                    self._revise(old,{**data,'status':status},now,run_id)
                    counts['weakened_count' if status=='weakened' and old['status']!='weakened' else 'revised_count'] += 1
                if rows:
                    db.execute('INSERT INTO consolidation_state VALUES(1,?) ON CONFLICT(singleton) DO UPDATE SET last_belief_id=excluded.last_belief_id',
                               (rows[-1]['id'],))
                self._finish_run(run_id,'completed_with_errors' if counts['failed_count'] else 'completed',counts,result)
                db.commit()
            except BaseException as error:
                db.rollback()
                # A failed audit write may itself propagate if storage is unusable.
                with db:
                    self._finish_run(run_id,'failed',dict.fromkeys(COUNT_FIELDS,0) | {'failed_count':1},
                                     {'error':f'{type(error).__name__}: {error}'[:300]})
                raise
            return self.get_run(run_id)

    def _revise(self, old, data, now, run_id):
        db = self.memory.db
        db.execute('INSERT INTO semantic_memory_history VALUES(?,?,?,?)',
                   (old['id'],old['revision'],now,json.dumps(dict(old),sort_keys=True,allow_nan=False)))
        data = {**data,'revision':old['revision']+1,'updated_at':now}
        db.execute(f'UPDATE semantic_memories SET {",".join(key+"=?" for key in data)} WHERE id=?',
                   (*data.values(),old['id']))
        emit(db,'SEMANTIC_MEMORY','semantic_memory','Semantic memory revised',
             dict(run_id=run_id,semantic_memory_id=old['id'],source_belief_id=old['source_belief_id'],
                  revision=data['revision'],status=data['status']))

    def _finish_run(self, run_id, status, counts, result):
        self.memory.db.execute(f'''UPDATE consolidation_runs SET completed_at=?,status=?,result_json=?,
            {','.join(key+'=?' for key in COUNT_FIELDS)} WHERE id=?''',
            (self.clock(),status,json.dumps(result,sort_keys=True,allow_nan=False),*(counts[key] for key in COUNT_FIELDS),run_id))
        emit(self.memory.db,'CONSOLIDATION','semantic_memory','Consolidation '+status,
             dict(run_id=run_id,status=status,**counts))

    def get_run(self, run_id):
        with self.memory._lock:
            row = dict(self.memory.db.execute('SELECT * FROM consolidation_runs WHERE id=?',(run_id,)).fetchone())
        row['result'] = json.loads(row.pop('result_json'))
        return row
