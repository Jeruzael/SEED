"""Strict frozen B8 evidence contracts, shared by writer and read-only observer.

This module deliberately performs no inference, scoring or historical reranking.
"""
import hashlib
import json
import math
import re
from .learner import ACTIONS, state_key

MAX_BYTES = 16384
MAX_ID = 2**63 - 1
TARGETS = ('battery_pct', 'load_ratio', 'disk_free_pct')
CURRENT_KEYS = ('battery_pct', 'charging', 'load_ratio', 'disk_free_pct', 'local_hour')
CONTRACT = dict(model='transition_delta_v1', model_version=1, horizon='next_post_action_observation')
HISTORY_REASONS = ('history_read_error', 'history_budget_exceeded', 'oversized_history', 'invalid_prediction')
GUARDS = ('high_load', 'low_battery', 'low_disk', 'unknown_resources')
TOP = ('model model_version weights_version decision_id transition_id created_at selected_at state_key current history '
       'prediction_contract selected_prediction_sha256 epsilon alpha random_draw choice_index policy_basis selection_mode '
       'eligible_actions selection_candidates selected_action fallback_reason candidates').split()


def require(ok):
    if not ok:
        raise ValueError('invalid_decision')


def number(value, low=None, high=None):
    try:
        return (type(value) in (int, float) and math.isfinite(value)
                and (low is None or value >= low) and (high is None or value <= high))
    except OverflowError:
        return False


def integer(value, low=0, high=MAX_ID):
    return type(value) is int and low <= value <= high


def keys(value, fields):
    require(type(value) is dict and set(value) == set(fields))


def compact(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('utf-8')


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result)
        result[key] = value
    return result


def strict_json(payload):
    require(isinstance(payload, (str, bytes)) and len(payload.encode('utf-8') if isinstance(payload, str) else payload) <= MAX_BYTES)
    try:
        return json.loads(payload, object_pairs_hook=_pairs, parse_constant=lambda _: require(False))
    except (TypeError, UnicodeError, RecursionError, OverflowError) as error:
        raise ValueError('invalid_decision') from error


def _structure(value):
    entries = 0
    def visit(item, depth):
        nonlocal entries
        require(depth <= 8)
        if type(item) is dict:
            entries += len(item)
            for k, v in item.items():
                require(type(k) is str and len(k.encode('utf-8')) <= 128)
                visit(v, depth+1)
        elif type(item) is list:
            require(len(item) <= 4)
            entries += len(item)
            for v in item:
                visit(v, depth+1)
        elif type(item) is str:
            require(len(item.encode('utf-8')) <= 128)
        elif item is not None and type(item) is not bool:
            require(number(item))
        require(entries <= 512)
    visit(value, 1)
    require(len(compact(value)) <= MAX_BYTES)


def validate_state(state):
    """Detach without sensor defaults; only B8's current domains are restricted."""
    try:
        require(type(state) is dict and all(type(k) is str for k in state))
        payload = json.dumps(state, sort_keys=True, ensure_ascii=True, allow_nan=False)
        require(len(payload.encode('utf-8')) <= MAX_BYTES)
        result = strict_json(payload)
        for target in TARGETS:
            if target in result:
                value = result[target]
                require((target == 'battery_pct' and value is None) or number(value, 0, None if target == 'load_ratio' else 100))
        for key in ('charging', 'network'):
            if key in result:
                require(result[key] is None or type(result[key]) is bool)
        if 'local_hour' in result:
            require(integer(result['local_hour'], 0, 23))
        return result
    except (ValueError, TypeError, OverflowError, RecursionError) as error:
        raise ValueError('invalid_state') from error


def projection(state):
    return {key: state[key] for key in CURRENT_KEYS if key in state}


def validate_prediction(prediction, action=None):
    _structure(prediction)
    keys(prediction, (*CONTRACT, 'action', 'signals'))
    require(all(prediction[k] == v and type(prediction[k]) is type(v) for k,v in CONTRACT.items()))
    require(prediction['action'] in ACTIONS and (action is None or prediction['action'] == action))
    keys(prediction['signals'], (*TARGETS, 'network_reachable'))
    for target, signal in prediction['signals'].items():
        require(type(signal) is dict)
        count = signal.get('evidence_count')
        require(integer(count, 0, 200))
        require(number(signal.get('confidence'), 0, .95) and signal['confidence'] == min(.95, count/20))
        require(signal.get('confidence_kind') == 'evidence_support')
        base = ('status', 'evidence_count', 'confidence', 'confidence_kind')
        if signal.get('status') == 'unavailable':
            keys(signal, (*base, 'reason'))
            require(signal['reason'] in ('missing_current_value','invalid_current_value') and count == 0)
            continue
        require(signal.get('status') == 'predicted')
        method = signal.get('method')
        require(count == 0 if method == 'persistence' else count >= 2)
        if target in TARGETS:
            keys(signal, (*base, 'value', 'method', 'clamped'))
            require(method in ('persistence','action_mean_delta','global_mean_delta'))
            require(type(signal['clamped']) is bool and number(signal['value'],0,None if target == 'load_ratio' else 100))
        else:
            require(method in ('persistence','action_boolean_frequency','global_boolean_frequency'))
            keys(signal, (*base,'value','method', *(() if method == 'persistence' else ('probability_true',))))
            require(type(signal['value']) is bool)
            if method != 'persistence':
                require(number(signal['probability_true'],0,1) and signal['value'] == (signal['probability_true'] >= .5))
    return prediction


def prediction_digest(prediction):
    validate_prediction(prediction)
    return hashlib.sha256(json.dumps(prediction,sort_keys=True,ensure_ascii=True,allow_nan=False).encode('utf-8')).hexdigest()


def canonical_actions(actions):
    require(type(actions) is list and actions == [a for a in ACTIONS if a in actions])


def validate_record(record, *, prediction, state_before, draft=False, mirrors=None):
    """Validate frozen facts and linkage only; never recompute decision utilities."""
    _structure(record)
    keys(record, TOP)
    require(record['model'] == 'decision_v1')
    require(type(record['model_version']) is int and record['model_version'] == 1)
    require(type(record['weights_version']) is int and record['weights_version'] == 1)
    require(type(record['decision_id']) is str and re.fullmatch('[0-9a-f]{32}',record['decision_id']))
    require(type(record['selected_prediction_sha256']) is str and re.fullmatch('[0-9a-f]{64}',record['selected_prediction_sha256']))
    tid = record['transition_id']
    require(tid is None if draft else integer(tid,1))
    require(record['created_at'] is None if draft else number(record['created_at'],0))
    require(number(record['selected_at'],0))
    state = validate_state(state_before)
    require(type(record['current']) is dict and record['current'] == projection(state))
    # bool/number and numeric representation matter in source linkage.
    require(compact(record['current']) == compact(projection(state)))
    require(record['state_key'] == state_key(record['current']))
    require(record['prediction_contract'] == CONTRACT)
    require(type(record['prediction_contract']['model_version']) is int)
    require(number(record['epsilon'],0,1) and number(record['alpha'],0,1) and record['alpha'] > 0)
    require(number(record['random_draw'],0,1) and record['random_draw'] < 1)
    history = record['history']
    keys(history, ('status','reason','cutoff_transition_id','raw_rows_examined'))
    count, cutoff = history['raw_rows_examined'], history['cutoff_transition_id']
    require(integer(count,0,200) and ((count == 0 and cutoff is None) or (count > 0 and integer(cutoff,1))))
    require(draft or cutoff is None or cutoff < tid)
    if history['status'] == 'ok':
        require(count > 0 and history['reason'] is None)
    elif history['status'] == 'empty':
        require(count == 0 and history['reason'] is None)
    else:
        require(history['status'] == 'unavailable' and history['reason'] in HISTORY_REASONS)
        if history['reason'] in HISTORY_REASONS[:2]:
            require(count == 0)
    keys(record['candidates'], ACTIONS)
    eligible = []
    for action,candidate in record['candidates'].items():
        keys(candidate, ('eligible','constraint_reasons','q_value','visits','q_missing','components','decision_utility','resource_forecasts'))
        require(type(candidate['eligible']) is bool and type(candidate['q_missing']) is bool)
        reasons = candidate['constraint_reasons']
        require(type(reasons) is list and reasons == [r for r in GUARDS if r in reasons])
        require(candidate['eligible'] == (not reasons))
        if action in ('observe','rest'):
            require(not reasons)
        if candidate['eligible']:
            eligible.append(action)
        require(number(candidate['q_value']) and integer(candidate['visits'],0,MAX_ID-1))
        require(not candidate['q_missing'] or (candidate['q_value'] == 0 and candidate['visits'] == 0))
        keys(candidate['components'],('q_component','forecast_resource_risk','model_uncertainty'))
        require(all(number(v,0,1) for v in candidate['components'].values()) and number(candidate['decision_utility'],0,1))
        keys(candidate['resource_forecasts'],TARGETS)
        for target,signal in candidate['resource_forecasts'].items():
            keys(signal,('status','value','method','evidence_count','confidence','newest_source_transition_id','newest_source_completed_at','invalid_source_count'))
            n, confidence = signal['evidence_count'],signal['confidence']
            require(integer(n,0,200) and number(confidence,0,.95) and confidence == min(.95,n/20))
            invalid, sid, clock = signal['invalid_source_count'],signal['newest_source_transition_id'],signal['newest_source_completed_at']
            require(integer(invalid,0,n))
            if signal['status'] == 'unavailable':
                require(signal['value'] is None and signal['method'] is None and n == 0)
            else:
                require(number(signal['value'],0,None if target == 'load_ratio' else 100))
            if signal['status'] in ('unavailable','persistence'):
                require(n == 0 and invalid == 0 and sid is None and clock is None)
                require(signal['status'] != 'persistence' or signal['method'] == 'persistence')
            else:
                require(history['status'] == 'ok' and 2 <= n <= count and signal['method'] in ('action_mean_delta','global_mean_delta'))
                if invalid == n:
                    require(sid is None and clock is None)
                else:
                    require(integer(sid,1,cutoff) and (draft or sid < tid) and number(clock,0))
                expected = 'invalid' if invalid or clock > record['selected_at'] else 'stale' if record['selected_at']-clock > 300 else 'usable'
                require(signal['status'] == expected)
    canonical_actions(record['eligible_actions'])
    canonical_actions(record['selection_candidates'])
    require(record['eligible_actions'] == [a for a in ACTIONS if a in eligible])
    pool, action = record['selection_candidates'], record['selected_action']
    require(pool and all(a in eligible for a in pool) and action in pool)
    index = record['choice_index']
    require((len(pool)==1 and index is None and action==pool[0]) or
            (len(pool)>1 and integer(index,0,len(pool)-1) and action==pool[index]))
    basis, mode, reason = record['policy_basis'],record['selection_mode'],record['fallback_reason']
    require(basis in ('composite','legacy_q'))
    # Support/status and failure provenance are frozen structural facts. This
    # does not recalculate components, rank candidates, or certify the pool.
    supported = any(s['status']=='usable' for a in eligible
                    for s in record['candidates'][a]['resource_forecasts'].values())
    require(basis == ('composite' if supported else 'legacy_q'))
    require(reason == (None if supported else history['reason'] or 'no_supported_resource_forecast'))
    require((basis=='composite' and reason is None) or (basis=='legacy_q' and reason in (*HISTORY_REASONS,'no_supported_resource_forecast','no_eligible_candidate')))
    if record['random_draw'] < record['epsilon']:
        require(mode=='explore' and pool==record['eligible_actions'])
    else:
        require(mode == ('exploit' if basis=='composite' else 'fallback'))
    validate_prediction(prediction,action)
    require(prediction_digest(prediction)==record['selected_prediction_sha256'])
    for target in TARGETS:
        signal, full = record['candidates'][action]['resource_forecasts'][target],prediction['signals'][target]
        require(signal['value']==full.get('value') and signal['method']==full.get('method') and
                signal['evidence_count']==full['evidence_count'] and signal['confidence']==full['confidence'])
        require(compact(signal['value']) == compact(full.get('value')))
    if mirrors is not None:
        for key in ('transition_id','created_at','model','model_version','selected_action','selection_mode'):
            if key == 'created_at':
                require(number(mirrors[key],0) and mirrors[key]==record[key])
            else:
                require(type(mirrors[key]) is type(record[key]) and mirrors[key]==record[key])
        require(mirrors['action']==action)
    return record
