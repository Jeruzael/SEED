"""Scoped read-only work limits and strict stored-data decoding for Astra."""
from contextlib import contextmanager
import json
import math
import sqlite3

from .read_store import ServiceError

MAX_ID = 2**63 - 1


def integer(value, minimum=0, maximum=MAX_ID):
    return type(value) is int and minimum <= value <= maximum


def number(value, minimum=None, maximum=None):
    try:
        return (type(value) in (int, float) and math.isfinite(value)
                and (minimum is None or value >= minimum)
                and (maximum is None or value <= maximum))
    except OverflowError:
        return False


def compact(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(',', ':')).encode('utf-8')


def capped(value, limit, error_code='invalid_evidence_response'):
    try:
        if len(compact(value)) <= limit:
            return value
    except (ValueError, TypeError, OverflowError, UnicodeError, RecursionError):
        pass
    raise ServiceError(error_code, 'Stored evidence exceeds its bounded response contract.', 503)


def strict_json(raw, limit=16384, array_limit=100, history=False):
    if type(raw) is str:
        raw = raw.encode('utf-8')
    if type(raw) is not bytes or len(raw) > limit:
        raise ValueError('invalid_json_bytes')
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate_key')
            result[key] = value
        return result
    def constant(_):
        raise ValueError('invalid_number')
    value = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
    if not isinstance(value, dict):
        raise ValueError('invalid_root')
    nodes = 0
    def check(item, depth=0, key=None):
        nonlocal nodes
        if depth > 8:
            raise ValueError('json_depth')
        if isinstance(item, dict):
            nodes += len(item)
            for name, child in item.items():
                if len(name.encode('utf-8')) > 128:
                    raise ValueError('json_key')
                check(child, depth+1, name if history and depth == 0 else None)
        elif isinstance(item, list):
            nodes += len(item)
            if len(item) > array_limit:
                raise ValueError('json_array')
            for child in item:
                check(child, depth+1)
        elif isinstance(item, str):
            if len(item.encode('utf-8')) > (16384 if key == 'payload_json' else 256):
                raise ValueError('json_string')
        elif item is not None and type(item) is not bool and not number(item):
            raise ValueError('json_number')
        if nodes > 512:
            raise ValueError('json_members')
    check(value)
    if len(compact(value)) > limit:
        raise ValueError('json_canonical_bytes')
    return value


@contextmanager
def bounded_read(store, error_code='evidence_read_unavailable', budget=300000):
    try:
        with store.connection() as db:
            ticks = 0
            def progress():
                nonlocal ticks
                ticks += 1000
                return ticks >= budget
            db.execute('PRAGMA busy_timeout=0')
            db.set_progress_handler(progress, 1000)
            try:
                db.execute('BEGIN')
                yield db
            except sqlite3.Error as error:
                raise ServiceError(error_code, 'Stored evidence is temporarily unavailable.', 503) from error
            finally:
                db.set_progress_handler(None, 0)
                if db.in_transaction:
                    db.rollback()
    except ServiceError as error:
        if error.code == 'database_unavailable' or (error.code == 'missing_database' and error_code != 'prediction_read_unavailable'):
            raise ServiceError(error_code, 'Stored evidence is temporarily unavailable.', 503) from error
        raise


def schema(db, tables):
    names = ('seed_schema', *tables)
    marks = ','.join('?' for _ in names)
    found = {r[0] for r in db.execute(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name IN ({marks}) LIMIT ?", (*names, len(names)))}
    if 'seed_schema' not in found:
        return 0, found
    versions = db.execute('SELECT version FROM seed_schema LIMIT 2').fetchall()
    if len(versions) != 1 or not integer(versions[0][0], 1, 7):
        raise ServiceError('incompatible_schema', 'Stored evidence uses an incompatible schema.', 409)
    return versions[0][0], found


# Layouts are static SQL identifiers. Numeric storage is gated in SQLite so a
# corrupt TEXT/BLOB in a numeric column never crosses the bounded projection.
def layout(integers='', numbers='', texts='', **special):
    return {**dict.fromkeys(integers.split(), 'i'), **dict.fromkeys(numbers.split(), 'n'),
            **dict.fromkeys(texts.split(), 128), **special}


WORLD = layout('id evidence_count contradiction_count source_first_transition_id source_last_transition_id model_version',
    'confidence created_at updated_at', 'belief_key signal scope scope_value belief_type', value_json=16384)
CURIOSITY = layout('transition_id model_version reflection_eligible reflection_claimed reflection_completed',
    'created_at', 'model status level', components_json=16384,
    **dict.fromkeys('score prediction_surprise uncertainty novelty coverage claimed_at completed_at'.split(), 'n?'),
    suppression_reason=(256, True), failure_reason=(256, True))
SEMANTIC = layout('id evidence_count contradiction_count source_belief_id source_belief_model_version source_first_transition_id source_last_transition_id revision model_version',
    'confidence source_belief_updated_at created_at updated_at',
    'semantic_key signal scope scope_value semantic_type source_fingerprint status model', payload_json=16384)
HISTORY = layout('semantic_memory_id revision', 'recorded_at', record_json=32768)
RUN = layout('id model_version source_beliefs_examined eligible_beliefs created_count revised_count weakened_count unchanged_count failed_count',
    'started_at', 'model provenance status', completed_at='n?', result_json=16384)


def projection(fields, alias='', prefix=''):
    parts, checks = [], []
    for key, kind in fields.items():
        col = f'{alias}.{key}' if alias else key
        nullable = isinstance(kind, tuple) or kind in ('i?', 'n?')
        base = kind[0] if isinstance(kind, tuple) else kind
        types = "'text'" if type(base) is int else ("'integer'" if base.startswith('i') else "'integer','real'")
        types += ",'null'" if nullable else ""
        valid = f"typeof({col}) IN ({types})"
        checks.append(valid)
        value = f"CASE WHEN {col} IS NULL THEN NULL ELSE COALESCE(substr(CAST({col} AS BLOB),1,{base+1}),X'') END" if type(base) is int else col
        parts.append(f'CASE WHEN {valid} THEN {value} END AS {prefix}{key}')
    parts.append(f'({" AND ".join(checks)}) AS {prefix}_types_valid')
    return ','.join(parts)


def scalars(row, fields, prefix=''):
    if row[prefix+'_types_valid'] != 1:
        raise ValueError('storage_type')
    item = {}
    for key, kind in fields.items():
        value = row[prefix+key]
        nullable = isinstance(kind, tuple) or kind in ('i?', 'n?')
        base = kind[0] if isinstance(kind, tuple) else kind
        if value is None and nullable:
            item[key] = None
            continue
        if type(base) is int:
            if type(value) is not bytes or len(value) > base:
                raise ValueError('text_size')
            value = value.decode('utf-8')
        elif not (integer(value) if base.startswith('i') else number(value)):
            raise ValueError('scalar')
        item[key] = value
    return item


def require(condition):
    if not condition:
        raise ValueError('stored_shape')


def statistics(item, value, semantic=False):
    from seed.world_model import SIGNALS, ACTIONS
    require(item['signal'] in SIGNALS and ((item['scope']=='global' and item['scope_value']=='') or
        (item['scope']=='action' and item['scope_value'] in ACTIONS)))
    boolean = item['signal']=='network_reachable'
    family = 'boolean_frequency' if boolean else 'numeric_delta'
    require(item['semantic_type' if semantic else 'belief_type']==family+('_summary' if semantic else ''))
    require(integer(item['evidence_count'], 2) and integer(item['contradiction_count'], 0, item['evidence_count']))
    require(number(item['confidence'], 0, .95) and item['model_version']==1)
    require(integer(item['source_first_transition_id'],1) and integer(item['source_last_transition_id'],item['source_first_transition_id']))
    keys = {'true_count','false_count','probability_true'} if boolean else {'mean_delta','mean_absolute_delta','min_delta','max_delta'}
    extra = {'interpretation'} if semantic else {'confidence_kind'}
    require(set(value)==keys | extra)
    if not semantic:require(value['confidence_kind']=='evidence_consistency')
    if boolean:
        require(integer(value['true_count']) and integer(value['false_count']) and number(value['probability_true'],0,1))
    else:
        require(all(number(value[k]) for k in keys) and value['mean_absolute_delta']>=0 and value['min_delta']<=value['mean_delta']<=value['max_delta'])
    if semantic:
        require(value['interpretation']==('observed_boolean_frequency' if boolean else 'observed_transition_delta'))


def validate(item, kind):
    for key in ('created_at','updated_at','source_belief_updated_at','started_at','completed_at','claimed_at'):
        if key in item and item[key] is not None:require(number(item[key],0))
    if kind in ('world','semantic'):
        payload = 'value' if kind=='world' else 'payload'
        statistics(item, item[payload], kind=='semantic')
        if kind=='world':
            require(item['belief_key']==f"1:{item['signal']}:{item['scope']}:{item['scope_value']}:{item['belief_type']}")
            item['confidence_kind']='evidence_consistency'
        else:
            require(item['model']=='semantic_v1' and item['status'] in ('active','weakened','source_unavailable'))
            require(integer(item['source_belief_id'],1) and integer(item['revision'],1) and item['source_belief_model_version']==1)
            require(len(item['source_fingerprint'])==64 and all(c in '0123456789abcdef' for c in item['source_fingerprint']))
    elif kind=='curiosity':
        require(item['model']=='curiosity_v1' and item['model_version']==1)
        require(item['status'] in ('evaluated','unavailable') and item['level'] in ('LOW','NOTABLE','HIGH','VERY_HIGH','UNAVAILABLE'))
        require((item['status']=='unavailable' and item['score'] is None and item['level']=='UNAVAILABLE') or
                (item['status']=='evaluated' and number(item['score'],0,1) and item['level'] in ('LOW','NOTABLE','HIGH','VERY_HIGH')))
        for key in ('score','prediction_surprise','uncertainty','novelty','coverage'):
            require(item[key] is None or number(item[key],0,1))
        for key in ('reflection_eligible','reflection_claimed','reflection_completed'):
            require(item[key] in (0,1))
        require(item['reflection_completed']<=item['reflection_claimed'])
        signals = item['components'].get('signals')
        require(set(item['components'])=={'signals'} and isinstance(signals,dict))
        from seed.world_model import SIGNALS, ACTIONS
        for signal, part in signals.items():
            require(signal in SIGNALS and isinstance(part,dict) and set(part)=={'sample','prior_belief','uncertainty','novelty','contradictory'})
            require(type(part['sample']) is bool if signal=='network_reachable' else number(part['sample']))
            require(number(part['uncertainty'],0,1) and number(part['novelty'],0,1) and type(part['contradictory']) is bool)
            prior=part['prior_belief']
            if prior is not None:
                require(isinstance(prior,dict) and set(prior)=={'belief_key','scope','scope_value','evidence_count','confidence','source_last_transition_id','value'})
                require(type(prior['belief_key']) is str and integer(prior['evidence_count'],2) and integer(prior['source_last_transition_id'],1) and number(prior['confidence'],0,.95))
                require((prior['scope']=='global' and prior['scope_value']=='') or (prior['scope']=='action' and prior['scope_value'] in ACTIONS))
                require(isinstance(prior['value'],dict))
    elif kind=='run':
        require(item['model']=='semantic_v1' and item['model_version']==1)
        require(item['status'] in ('running','suppressed','completed','completed_with_errors','failed'))
        require(item['provenance'] in ('policy_selected','owner_requested'))
        result=item['result']
        if set(result)=={'error'}:
            require(type(result['error']) is str)
        else:
            require(set(result)=={'reason','examined_ids','failures'})
            require(result['reason'] is None or type(result['reason']) is str)
            require(isinstance(result['examined_ids'],list) and all(integer(i,1) for i in result['examined_ids']))
            require(isinstance(result['failures'],list))
            for failure in result['failures']:
                require(isinstance(failure,dict) and set(failure)=={'source_belief_id','reason'} and integer(failure['source_belief_id'],1) and type(failure['reason']) is str)


LAYOUTS = {'world':WORLD,'curiosity':CURIOSITY,'semantic':SEMANTIC,'history':HISTORY,'run':RUN}
PAYLOADS = {'world':('value_json','value'),'curiosity':('components_json','components'),
            'semantic':('payload_json','payload'),'history':('record_json','record'),'run':('result_json','result')}


def stored_record(row, kind, prefix=''):
    fields = LAYOUTS[kind]
    raw_key, payload_key = PAYLOADS[kind]
    ids = ('semantic_memory_id','revision') if kind=='history' else ('transition_id',) if kind=='curiosity' else ('id',)
    marker = {key:row[prefix+key] for key in ids if integer(row[prefix+key],1)}
    try:
        require(len(marker)==len(ids))
        item = scalars(row,fields,prefix)
        item[payload_key] = strict_json(item.pop(raw_key), limit=32768 if kind=='history' else 16384, history=kind=='history')
        if kind=='history':
            snapshot = item['record']
            require(set(snapshot)==set(SEMANTIC))
            # History contains the original SQL row, including its JSON string.
            encoded = {key: value.encode('utf-8') if type(value) is str else value for key,value in snapshot.items()}
            encoded['_types_valid']=1
            record = stored_record(encoded,'semantic')
            require(record.get('read_status')!='corrupt' and record['id']==item['semantic_memory_id'] and record['revision']==item['revision'])
            item['record']=record
        else:
            validate(item,kind)
        require(len(compact(item)) <= (34816 if kind=='history' else 18432))
        return item
    except (ValueError,TypeError,KeyError,OverflowError,UnicodeError,RecursionError):
        return {**marker,'read_status':'corrupt','read_reason':'invalid_stored_evidence',payload_key:None}


def feature(db, table, minimum, extra=()):
    version, tables = schema(db,(table,*extra))
    if version < minimum:
        return dict(available=False,items=[],next_cursor=None), tables
    if table not in tables:
        return dict(available=False,status='error',reason='missing_feature_table',items=[],next_cursor=None), tables
    return None, tables


def page(db, table, kind, where, args, limit, descending=False, select=None, source=None):
    key = 'transition_id' if kind=='curiosity' else 'id'
    ids = [r[0] for r in db.execute(f'SELECT {key} FROM {table} WHERE {where} ORDER BY {key} {"DESC" if descending else "ASC"} LIMIT ?', (*args,limit+1))]
    chosen = ids[:limit]
    rows = []
    if chosen:
        marks = ','.join('?' for _ in chosen)
        rows = db.execute(f'SELECT {select or projection(LAYOUTS[kind],"m")} FROM {source or table+" m"} WHERE m.{key} IN ({marks}) ORDER BY m.{key} {"DESC" if descending else "ASC"}', chosen).fetchall()
    items = [stored_record(r,kind) for r in rows]
    result = dict(available=True,items=items,next_cursor=(chosen[-1]-(1 if descending else 0)) if len(ids)>limit else None)
    return result, rows
