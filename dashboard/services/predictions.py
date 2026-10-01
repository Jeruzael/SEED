"""B1/B2/B3 history projection; no inference, evaluation, sensing or writes."""
from .evidence_reads import (MAX_ID, integer, number, strict_json, compact, capped,
                             bounded_read, schema)
from .read_store import ServiceError

READ_BUDGET = 300000
ACTIONS = ('observe', 'reflect', 'consolidate', 'rest')
TARGETS = ('battery_pct', 'load_ratio', 'disk_free_pct', 'network_reachable')
METADATA = '''t.id AS transition_id,
 CASE WHEN typeof(t.episode_id)='integer' THEN t.episode_id END AS episode_id,
 e.id AS linked_episode,
 CASE WHEN typeof(t.started_at) IN ('integer','real') THEN t.started_at END AS started_at,
 CASE WHEN typeof(t.completed_at) IN ('integer','real') THEN t.completed_at END AS completed_at,
 CASE WHEN typeof(t.legacy_reward) IN ('integer','real') THEN t.legacy_reward END AS legacy_reward,
 CASE WHEN t.action IN ('observe','reflect','consolidate','rest') THEN t.action END AS action'''
JOIN = ' FROM transitions t LEFT JOIN episodes e ON e.id=t.episode_id'
PRESENCE = ', t.prediction_json IS NOT NULL AS prediction_present, t.prediction_error_json IS NOT NULL AS evaluation_present'
PAYLOAD = ''', substr(CAST(t.prediction_json AS BLOB),1,16385) AS prediction,
 substr(CAST(t.prediction_error_json AS BLOB),1,16385) AS evaluation,
 typeof(t.prediction_json) AS prediction_type, typeof(t.prediction_error_json) AS evaluation_type'''


def require(condition):
    if not condition:
        raise ValueError('invalid_shape')


def keys(value, required, optional=()):
    require(type(value) is dict and set(required) <= value.keys() <= set(required) | set(optional))


def target_value(value, target):
    return type(value) is bool if target == 'network_reachable' else number(value, 0, None if target == 'load_ratio' else 100)


def validate_prediction(p, action):
    keys(p, ('action','signals','model','model_version','horizon'))
    require(p['action'] == action)
    keys(p['signals'], TARGETS)
    for target, signal in p['signals'].items():
        require(type(signal) is dict)
        support = ('status','evidence_count','confidence','confidence_kind')
        require(integer(signal.get('evidence_count'), 0, 200) and number(signal.get('confidence'), 0, .95)
                and signal.get('confidence_kind') == 'evidence_support')
        if signal.get('status') == 'unavailable':
            keys(signal, (*support,'reason'))
            require(type(signal['reason']) is str and bool(signal['reason']))
        else:
            require(signal.get('status') == 'predicted' and target_value(signal.get('value'), target))
            if target == 'network_reachable':
                keys(signal, (*support,'value','method'), ('probability_true',))
                require(signal['method'] in ('persistence','action_boolean_frequency','global_boolean_frequency'))
                require('probability_true' not in signal or number(signal['probability_true'], 0, 1))
            else:
                keys(signal, (*support,'value','method','clamped'))
                require(signal['method'] in ('persistence','action_mean_delta','global_mean_delta') and type(signal['clamped']) is bool)


def validate_evaluation(e):
    keys(e, ('signals','aggregate','prediction_model','prediction_model_version','horizon','evaluator','evaluator_version'))
    source_header = (e['prediction_model'],e['prediction_model_version'],e['horizon'])
    require(source_header == (None,None,None) or
            (source_header == ('transition_delta_v1',1,'next_post_action_observation')
             and type(e['prediction_model_version']) is int))
    keys(e['signals'], TARGETS)
    for target, signal in e['signals'].items():
        require(type(signal) is dict)
        if signal.get('status') == 'not_evaluated':
            keys(signal, ('status','reason'))
            require(type(signal['reason']) is str and bool(signal['reason']))
            continue
        require(signal.get('status') == 'evaluated')
        required = ('status','predicted','actual','normalized_error','scoring_method')
        require(target_value(signal.get('predicted'),target) and target_value(signal.get('actual'),target)
                and number(signal.get('normalized_error'),0,1))
        if target == 'network_reachable':
            method=signal.get('scoring_method')
            require(method in ('boolean_mismatch','boolean_brier'))
            extra=('probability_true','brier_error') if method == 'boolean_brier' else ()
            keys(signal, (*required,'correct','classification_error',*extra))
            require(type(signal['correct']) is bool and integer(signal['classification_error'],0,1))
            for field in extra:
                require(number(signal[field],0,1))
        else:
            keys(signal, (*required,'signed_error','absolute_error'))
            require(number(signal['signed_error']) and number(signal['absolute_error'],0))
            require(signal['scoring_method'] == ('bounded_relative' if target=='load_ratio' else 'percentage_range'))
    a=e['aggregate']
    keys(a, ('status','evaluated_signals','target_signals','coverage','mean_normalized_error','accuracy_score'))
    require(a['status'] in ('evaluated','unavailable') and integer(a['evaluated_signals'],0,4)
            and type(a['target_signals']) is int and a['target_signals']==4 and number(a['coverage'],0,1))
    for field in ('mean_normalized_error','accuracy_score'):
        require(a[field] is None or number(a[field],0,1))
        if a['status']=='unavailable':
            require(a[field] is None)


def payload(row, kind, action):
    if row[kind+'_type'] == 'null':
        return dict(status='absent', reason='not_recorded', data=None)
    try:
        require(row[kind+'_type']=='text')
        value=strict_json(row[kind], array_limit=64)
        model_key,version_key=('model','model_version') if kind=='prediction' else ('evaluator','evaluator_version')
        require(type(value.get(model_key)) is str and integer(value.get(version_key),1))
        if kind=='prediction':
            require(type(value.get('horizon')) is str)
        model='transition_delta_v1' if kind=='prediction' else 'prediction_error_v1'
        if (value[model_key]!=model or value[version_key]!=1 or
            kind=='prediction' and value['horizon']!='next_post_action_observation'):
            return dict(status='unsupported',reason='unsupported_model',data=None)
        if kind=='prediction':
            validate_prediction(value,action)
        else:
            validate_evaluation(value)
        return dict(status='stored',reason=None,data=value)
    except (ValueError, TypeError, KeyError, OverflowError, UnicodeError, RecursionError):
        return dict(status='corrupt',reason='invalid_'+kind,data=None)


def metadata(row):
    require(integer(row['transition_id'],1) and integer(row['episode_id'],1)
            and row['linked_episode']==row['episode_id'] and row['action'] in ACTIONS
            and number(row['started_at'],0) and number(row['completed_at'],row['started_at'])
            and number(row['legacy_reward']))
    return {key:row[key] for key in ('episode_id','started_at','completed_at','action','legacy_reward')}


def record(row, detail):
    tid=row['transition_id']
    try:
        fields=metadata(row)
    except ValueError:
        result=dict(available=False,status='error',reason='invalid_transition',transition_id=tid)
        if detail:
            result.update(transition=None,prediction=None,evaluation=None)
        return result
    result=dict(available=True,status='stored',reason=None,transition_id=tid)
    if not detail:
        result.update(fields,prediction_present=bool(row['prediction_present']),evaluation_present=bool(row['evaluation_present']))
        require(len(compact(result))<=512)
    else:
        p=payload(row,'prediction',fields['action']);e=payload(row,'evaluation',fields['action'])
        if p['status']==e['status']=='stored':
            source=p['data'];evaluation=e['data']
            if any(evaluation[ek] is not None and evaluation[ek]!=source[pk]
                   for ek,pk in [('prediction_model','model'),('prediction_model_version','model_version'),('horizon','horizon')]):
                e=dict(status='corrupt',reason='invalid_evaluation',data=None)
        result.update(transition=fields,prediction=p,evaluation=e)
    return result


class PredictionReadService:
    def __init__(self, store):
        self.store=store

    def list(self, before=None, limit=20):
        if before is not None and not integer(before,1) or not integer(limit,1,50):
            raise ServiceError('invalid_query','Invalid prediction cursor or limit.')
        return self._read(False,MAX_ID if before is None else before,limit)

    def detail(self, transition_id):
        if not integer(transition_id,1):
            raise ServiceError('invalid_query','Invalid transition ID.')
        return self._read(True,transition_id,1)

    def _read(self, detail, cursor, limit):
        def absent(status,reason):
            result=dict(available=False,status=status,reason=reason)
            if detail:
                result.update(transition_id=cursor,transition=None,prediction=None,evaluation=None)
            else:
                result.update(items=[],next_cursor=None)
            return result
        try:
            with bounded_read(self.store,'prediction_read_unavailable',READ_BUDGET) as db:
                version,tables=schema(db,('transitions','episodes'))
                if version<2:
                    return absent('unavailable','legacy_schema')
                for table,reason in [('transitions','missing_transition_table'),('episodes','missing_episode_table')]:
                    if table not in tables:
                        return absent('error',reason)
                if detail:
                    row=db.execute('SELECT '+METADATA+PAYLOAD+JOIN+' WHERE t.id=?',(cursor,)).fetchone()
                    if row is None:
                        raise ServiceError('prediction_not_found','No transition exists for this ID.',404)
                    result=record(row,True)
                else:
                    ids=[r[0] for r in db.execute('SELECT id FROM transitions WHERE id<=? ORDER BY id DESC LIMIT ?', (cursor,limit+1))]
                    next_cursor=ids[limit] if len(ids)>limit else None
                    ids=ids[:limit];rows=[]
                    if ids:
                        rows=db.execute('SELECT '+METADATA+PRESENCE+JOIN+' WHERE t.id IN ('+','.join('?' for _ in ids)+') ORDER BY t.id DESC',ids).fetchall()
                    result=dict(available=True,status='stored',reason=None,items=[record(r,False) for r in rows],next_cursor=next_cursor)
                return capped(result,35840 if detail else 27648,'invalid_prediction_response')
        except ServiceError as error:
            if error.code=='missing_database':
                return absent('unavailable','missing_home')
            raise
