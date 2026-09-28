"""Bounded, descriptive self-model snapshots. No policy or sensing dependencies."""
from __future__ import annotations

from collections import Counter
from contextlib import contextmanager
import copy
import json
import logging
import math
import sqlite3
import time

from .telemetry import emit

MODEL = 'self_model_v1'
MODEL_VERSION = 1
SOURCE_BYTES = 16384
SNAPSHOT_BYTES = 32768
MAX_ID = 2**63 - 1
SENSORS = ('battery_pct', 'charging', 'load_ratio', 'load_5m_ratio', 'disk_free_pct',
           'network', 'hostname', 'machine', 'macos')
RESOURCES = ('battery_pct', 'charging', 'load_ratio', 'disk_free_pct', 'network')
ACTIONS = dict(observe='no_additional_processing', reflect='bounded_reflection',
               consolidate='guarded_semantic_consolidation', rest='post_cycle_wait')
UNSUPPORTED = ('arbitrary_tools', 'planning', 'self_modification')
STATUSES = ('available', 'unavailable', 'stale', 'error', 'not_supported', 'insufficient_evidence')
REASONS = (None, 'not_recorded', 'missing_timestamp', 'invalid_value', 'invalid_json',
           'oversized_source', 'invalid_timestamp', 'clock_regression', 'source_expired',
           'snapshot_expired', 'partial_window', 'invalid_evidence', 'no_supported_evaluations',
           'no_scored_evaluations', 'no_consolidation_run', 'missing_runtime', 'outside_action_contract')
COUNT_TABLES = dict(episode_count=('episodes', 'id'), transition_count=('transitions', 'id'),
                    world_model_queue_depth=('world_model_queue', 'transition_id'),
                    semantic_memory_count=('semantic_memories', 'id'))
RUN_COUNTS = ('source_beliefs_examined', 'created_count', 'revised_count', 'weakened_count',
              'unchanged_count', 'failed_count')
SIGNALS = ('battery_pct', 'load_ratio', 'disk_free_pct', 'network_reachable')
log = logging.getLogger('seed')


def number(value, low=0, high=None):
    try:
        return type(value) in (int, float) and math.isfinite(value) and value >= low and (high is None or value <= high)
    except (ValueError, OverflowError):
        return False


def integer(value, low=0, high=MAX_ID):
    return type(value) is int and low <= value <= high


def text(value):
    try:
        return isinstance(value, str) and 0 < len(value.encode('utf-8')) <= 128
    except UnicodeError:
        return False


def require(condition):
    if not condition:
        raise ValueError('invalid_snapshot')


def keys(value, expected):
    require(type(value) is dict and set(value) == set(expected))


def bounded_json(raw, limit=SOURCE_BYTES):
    """Reject size, nesting, duplicate keys and nonfinite values before consumption."""
    if not isinstance(raw, (str, bytes)):
        raise ValueError('invalid_json')
    try:
        blob = raw.encode('utf-8') if isinstance(raw, str) else raw
        if len(blob) > limit:
            raise ValueError('oversized_source')
        string = blob.decode('utf-8')
        depth = 0
        quoted = escaped = False
        for char in string:
            if quoted:
                if escaped:
                    escaped = False
                elif char == '\\':
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char in '[{':
                depth += 1
                if depth > 12:
                    raise ValueError('invalid_json')
            elif char in ']}':
                depth -= 1
        members = 0
        def pairs(items):
            nonlocal members
            members += len(items)
            if members > 512 or len(dict(items)) != len(items):
                raise ValueError('invalid_json')
            return dict(items)
        def constant(_):
            raise ValueError('invalid_json')
        value = json.loads(string, object_pairs_hook=pairs, parse_constant=constant)
        def finite_tree(item):
            if type(item) is float and not math.isfinite(item):
                raise ValueError('invalid_json')
            if isinstance(item, list):
                if len(item) > 100:
                    raise ValueError('invalid_json')
                for child in item: finite_tree(child)
            elif isinstance(item, dict):
                for child in item.values(): finite_tree(child)
        finite_tree(value)
        if type(value) is not dict:
            raise ValueError('invalid_json')
        return value
    except (UnicodeError, RecursionError, OverflowError, json.JSONDecodeError) as error:
        raise ValueError('invalid_json') from error


def source(table, ids, observed, kind, ttl, **extra):
    return dict(table=table, ids=ids, source_observed_at=observed if number(observed) else None,
                timestamp_kind=kind, ttl_seconds=ttl, **extra)


def field(value, src, status='available', reason=None):
    return dict(value=value, status=status, reason=reason, source=src)


def _age(item, src, measured_at, now):
    if src['ttl_seconds'] is None:
        return item
    observed = src['source_observed_at']
    if now < measured_at or (observed is not None and observed > now):
        item.update(status='error', reason='clock_regression')
    elif item['status'] in ('available', 'stale'):
        if observed is None:
            item.update(status='unavailable', reason='missing_timestamp')
        elif now - observed > src['ttl_seconds']:
            item.update(status='stale', reason='source_expired')
        elif now - measured_at > src['ttl_seconds']:
            item.update(status='stale', reason='snapshot_expired')
    return item


def envelopes(p):
    yield from p['observations'].values()
    yield from p['capabilities']['actions'].values()
    yield from p['capabilities']['unsupported'].values()
    yield p['last_selected_action']
    yield from p['prediction_performance'].values()
    yield from p['memory'].values()
    yield p['recent_failures']


def sensor_valid(name, value):
    if name in ('charging', 'network'):
        return type(value) is bool
    if name in ('hostname', 'machine', 'macos'):
        return text(value)
    return number(value, 0, 100 if name in ('battery_pct', 'disk_free_pct') else None)


def _observations(row, now):
    try:
        state = bounded_json(row['state'])
        error = None
    except ValueError as exc:
        state, error = {}, str(exc)
    wall = state.get('wall_time')
    clock_error = ('invalid_timestamp' if wall is not None and not number(wall) else
                   'clock_regression' if number(wall) and wall > row['completed_at'] else None)
    results = {}
    for name in SENSORS:
        value = state.get(name)
        if error:
            item = field(None, 'observation', 'error', error)
        elif value is None or value == '' and type(value) is str:
            item = field(None, 'observation', 'unavailable', 'not_recorded')
        elif not sensor_valid(name, value):
            item = field(None, 'observation', 'error', 'invalid_value')
        elif clock_error:
            item = field(value, 'observation', 'error', clock_error)
        elif wall is None:
            item = field(value, 'observation', 'unavailable', 'missing_timestamp')
        else:
            item = field(value, 'observation')
        results[name] = item
    return results, source('transitions', [row['id']], wall, 'state_after.wall_time', 60)


def _evaluation(raw):
    p = bounded_json(raw)
    contract = dict(evaluator='prediction_error_v1', evaluator_version=1,
                    prediction_model='transition_delta_v1', prediction_model_version=1,
                    horizon='next_post_action_observation')
    for key, expected in contract.items():
        require(type(p.get(key)) is type(expected))
    if any(p[key] != value for key, value in contract.items()):
        return None
    signals, aggregate = p.get('signals'), p.get('aggregate')
    keys(signals, SIGNALS)
    require(type(aggregate) is dict)
    errors = []
    for name in SIGNALS:
        s = signals[name]
        require(type(s) is dict)
        if s.get('status') == 'not_evaluated':
            keys(s, ('status', 'reason'))
            require(s['reason'] in ('prediction_unavailable', 'invalid_prediction', 'actual_unavailable'))
            continue
        require(s.get('status') == 'evaluated' and number(s.get('normalized_error'), 0, 1))
        method = s.get('scoring_method')
        if name == 'network_reachable':
            require(type(s.get('correct')) is bool and integer(s.get('classification_error'), 0, 1))
            require(s['classification_error'] == int(not s['correct']))
            require(type(s.get('predicted')) is bool and type(s.get('actual')) is bool)
            require(s['correct'] == (s['predicted'] == s['actual']))
            if method == 'boolean_brier':
                require(number(s.get('brier_error'), 0, 1) and number(s.get('probability_true'), 0, 1))
                require(math.isclose(s['normalized_error'], s['brier_error'], abs_tol=1e-12, rel_tol=0))
            else:
                require(method == 'boolean_mismatch' and s['normalized_error'] == s['classification_error'])
        else:
            require(sensor_valid(name, s.get('predicted')) and sensor_valid(name, s.get('actual')))
            require(number(s.get('absolute_error')) and number(s.get('signed_error'), -float('inf')))
            require(method == ('bounded_relative' if name == 'load_ratio' else 'percentage_range'))
        errors.append(s['normalized_error'])
    n = len(errors)
    require(type(aggregate.get('target_signals')) is int and aggregate['target_signals'] == 4)
    require(type(aggregate.get('evaluated_signals')) is int and aggregate['evaluated_signals'] == n)
    require(number(aggregate.get('coverage'), 0, 1) and aggregate['coverage'] == n / 4)
    if not n:
        require(aggregate.get('status') == 'unavailable' and aggregate.get('mean_normalized_error') is None and aggregate.get('accuracy_score') is None)
    else:
        require(aggregate.get('status') == 'evaluated')
        mean = math.fsum(v / n for v in errors)
        require(number(aggregate.get('mean_normalized_error'), 0, 1) and number(aggregate.get('accuracy_score'), 0, 1))
        require(math.isclose(aggregate['mean_normalized_error'], mean, abs_tol=1e-12, rel_tol=0))
        require(math.isclose(aggregate['accuracy_score'], 1 - mean, abs_tol=1e-12, rel_tol=0))
    return aggregate


def _performance(rows, now):
    valid, scored = [], []
    counts = dict(raw_rows=len(rows), raw_transition_ids=sorted(r['id'] for r in rows),
                  valid_evaluations=0, missing_evaluations=0, unsupported_evaluations=0, invalid_evaluations=0)
    for row in rows:
        try:
            require(number(row['started_at'], 0, now) and number(row['completed_at'], row['started_at'], now))
            if row['evaluation'] is None:
                counts['missing_evaluations'] += 1
                continue
            aggregate = _evaluation(row['evaluation'])
            if aggregate is None:
                counts['unsupported_evaluations'] += 1
                continue
            valid.append((row, aggregate))
            if aggregate['status'] == 'evaluated': scored.append((row, aggregate))
            counts['valid_evaluations'] += 1
        except (ValueError, TypeError, KeyError, OverflowError):
            counts['invalid_evaluations'] += 1
    times = [r['completed_at'] for r in rows if number(r['completed_at'], 0, now)]
    sources = {'prediction_window': source('transitions', counts['raw_transition_ids'], now, 'query_snapshot', 300,
               oldest_completed_at=min(times) if times else None, newest_completed_at=max(times) if times else None)}
    performance = {'window': field(counts, 'prediction_window')}
    for label, samples in (('coverage', valid), ('score', scored)):
        n = len(samples)
        key = 'prediction_' + label
        sources[key] = source('transitions', sorted(r['id'] for r, _ in samples),
                              max((r['completed_at'] for r, _ in samples), default=None), 'newest_contributing_completion', 300)
        value = {'samples': n}
        for out, attr in ([('mean', 'coverage')] if label == 'coverage' else
                          [('mean_normalized_error', 'mean_normalized_error'), ('accuracy_score', 'accuracy_score')]):
            value[out] = math.fsum(a[attr] / n for _, a in samples) if n else None
        invalid = counts['invalid_evaluations'] > 0
        performance[label] = field(value, key, 'available' if n else 'error' if invalid else 'insufficient_evidence',
            'partial_window' if n and invalid else None if n else 'invalid_evidence' if invalid else
            'no_supported_evaluations' if label == 'coverage' else 'no_scored_evaluations')
    return performance, sources


def _bounded_text(raw):
    try:
        value = raw.decode('utf-8') if isinstance(raw, bytes) else raw
    except UnicodeError:
        return None
    return value if text(value) else None


def _consolidation(row, now):
    if row is None:
        return field(None, 'consolidation', 'unavailable', 'no_consolidation_run'), source('consolidation_runs', [], None, 'completed_at', 300)
    kind = 'started_at' if _bounded_text(row['status']) == 'running' else 'completed_at'
    src = source('consolidation_runs', [row['id']], row[kind], kind, 300)
    value = dict(run_id=row['id'], status=_bounded_text(row['status']), provenance=_bounded_text(row['provenance']),
                 started_at=row['started_at'], completed_at=row['completed_at'], suppression_reason=None,
                 **{key: row[key] for key in RUN_COUNTS})
    try:
        require(_bounded_text(row['model']) == 'semantic_v1' and type(row['model_version']) is int and row['model_version'] == 1)
        _valid_run(value)
        if any(number(row[key]) and row[key] > now for key in ('started_at', 'completed_at')):
            return field(value, 'consolidation', 'error', 'clock_regression'), src
        try:
            result = bounded_json(row['result'])
        except ValueError as exc:
            return field(value, 'consolidation', 'error', str(exc)), src
        if value['status'] == 'suppressed':
            require(result.get('reason') in ('high_load', 'low_battery', 'low_disk'))
            value['suppression_reason'] = result['reason']
        return field(value, 'consolidation'), src
    except ValueError as exc:
        return field(None, 'consolidation', 'error', 'oversized_source' if str(exc) == 'oversized_source' else 'invalid_value'), src


def _runtime(row, now):
    src = source('runtime', [1] if row else [], None, 'heartbeat', 10)
    if row is None:
        return field(None, 'runtime', 'unavailable', 'missing_runtime'), src
    try:
        data = bounded_json(row['data'])
        heartbeat, success, session = (data.get(k) for k in ('heartbeat', 'last_successful_cycle', 'session_id'))
        src['source_observed_at'] = heartbeat if number(heartbeat) else None
        if heartbeat is None:
            return field(None, 'runtime', 'unavailable', 'missing_timestamp'), src
        require(number(heartbeat) and (success is None or number(success)) and text(session))
        value = dict(heartbeat=heartbeat, last_successful_cycle=success, session_id=session)
        if heartbeat > now or success is not None and success > now:
            return field(value, 'runtime', 'error', 'clock_regression'), src
        return field(value, 'runtime'), src
    except ValueError:
        return field(None, 'runtime', 'error', 'invalid_value'), src


def _failures(rows, now):
    sample = rows[:100]
    valid, invalid = [], 0
    for row in sample:
        name = _bounded_text(row['source'])
        if number(row['ts'], 0, now) and name:
            valid.append(dict(id=row['id'], ts=row['ts'], category='ERROR', source=name))
        else:
            invalid += 1
    value = dict(count=len(sample), has_older_retained_errors=len(rows) > 100,
                 oldest_event_id=sample[-1]['id'] if sample else None,
                 newest_event_id=sample[0]['id'] if sample else None,
                 latest_valid_event=valid[0] if valid else None, invalid_metadata_count=invalid)
    return field(value, 'errors', 'error' if sample and not valid else 'available',
                 'invalid_value' if sample and not valid else 'partial_window' if invalid else None), \
        source('events', sorted(r['id'] for r in sample), now, 'query_snapshot', 60)


def build_snapshot(evidence, now, transition_id, session_id):
    """Pure calculation over a byte/row-bounded persisted evidence bundle."""
    require(number(now) and integer(transition_id, 1) and text(session_id))
    row = evidence['transition']
    require(row is not None and row['id'] == transition_id)
    require(number(row['started_at'], 0, now) and number(row['completed_at'], row['started_at'], now))
    action = _bounded_text(row['action'])
    require(action in ACTIONS)
    observations, observed = _observations(row, now)
    performance, perf_sources = _performance(evidence['evaluations'], now)
    consolidation, consolidation_source = _consolidation(evidence['consolidation'], now)
    runtime, runtime_source = _runtime(evidence['runtime'], now)
    failures, error_source = _failures(evidence['errors'], now)
    sources = dict(catalog=source(None, [], None, 'producer_contract', None, contract=MODEL),
        observation=observed, transition=source('transitions', [transition_id], row['completed_at'], 'completed_at', 60),
        **perf_sources, storage=source(None, [], now, 'query_snapshot', 60,
            tables=['seed_schema', 'episodes', 'transitions', 'world_model_queue', 'semantic_memories']),
        consolidation=consolidation_source, runtime=runtime_source, errors=error_source)
    storage = dict(schema_version=evidence['schema_version'], bounded_reads_succeeded=True,
                   page_size=evidence['page_size'], page_count=evidence['page_count'],
                   logical_allocated_bytes=evidence['page_size'] * evidence['page_count'])
    for key, ids in evidence['counts'].items():
        n = len(ids)
        storage[key] = dict(count=n, relation='at_least' if n == 1001 else 'exact')
    p = dict(model=MODEL, model_version=1, measured_at=now, source_transition_id=transition_id,
        source_event_id=evidence['event_cutoff'], source_session_id=session_id, sources=sources,
        capabilities=dict(sensors={k: dict(supported=True, reading='observations.' + k) for k in SENSORS},
            actions={k: field(dict(implemented=True, selectable=True, owner_controlled=True, work_kind=v), 'catalog') for k, v in ACTIONS.items()},
            unsupported={k: field(False, 'catalog', 'not_supported', 'outside_action_contract') for k in UNSUPPORTED}),
        observations=observations, resources={k: 'observations.' + k for k in RESOURCES},
        last_selected_action=field(action, 'transition'), prediction_performance=performance,
        memory=dict(storage=field(storage, 'storage'), latest_consolidation=consolidation, runtime_reported=runtime),
        recent_failures=failures)
    for item in envelopes(p): _age(item, sources[item['source']], now, now)
    validate_snapshot(p)
    return p


def _valid_run(v):
    keys(v, ('run_id', 'status', 'provenance', 'started_at', 'completed_at', 'suppression_reason', *RUN_COUNTS))
    require(integer(v['run_id'], 1) and v['status'] in ('running', 'suppressed', 'completed', 'completed_with_errors', 'failed'))
    require(v['provenance'] in ('policy_selected', 'owner_requested') and number(v['started_at']))
    require((v['completed_at'] is None if v['status'] == 'running' else number(v['completed_at'], v['started_at'])))
    require(all(integer(v[k], 0, 100) for k in RUN_COUNTS))
    require(v['suppression_reason'] in (None, 'high_load', 'low_battery', 'low_disk'))


def validate_snapshot(p):
    """Validate the complete stored v1 contract, including nested measurement domains."""
    keys(p, ('model', 'model_version', 'measured_at', 'source_transition_id', 'source_event_id', 'source_session_id',
             'sources', 'capabilities', 'observations', 'resources', 'last_selected_action', 'prediction_performance', 'memory', 'recent_failures'))
    require(p['model'] == MODEL and type(p['model_version']) is int and p['model_version'] == 1)
    require(number(p['measured_at']) and integer(p['source_transition_id'], 1) and integer(p['source_event_id']) and text(p['source_session_id']))
    sources = p['sources']
    policies = dict(catalog=(None, 'producer_contract', None), observation=('transitions', 'state_after.wall_time', 60),
        transition=('transitions', 'completed_at', 60), prediction_window=('transitions', 'query_snapshot', 300),
        prediction_coverage=('transitions', 'newest_contributing_completion', 300),
        prediction_score=('transitions', 'newest_contributing_completion', 300), storage=(None, 'query_snapshot', 60),
        consolidation=('consolidation_runs', None, 300), runtime=('runtime', 'heartbeat', 10), errors=('events', 'query_snapshot', 60))
    keys(sources, policies)
    for name, (table, kind, ttl) in policies.items():
        s = sources[name]
        extra = ('contract',) if name == 'catalog' else ('tables',) if name == 'storage' else ('oldest_completed_at', 'newest_completed_at') if name == 'prediction_window' else ()
        keys(s, ('table', 'ids', 'source_observed_at', 'timestamp_kind', 'ttl_seconds', *extra))
        require(s['table'] == table and (s['timestamp_kind'] == kind if kind else s['timestamp_kind'] in ('started_at', 'completed_at')))
        require(s['ttl_seconds'] == ttl and (ttl is None or type(s['ttl_seconds']) is int))
        require(type(s['ids']) is list and len(s['ids']) <= 100 and all(integer(i, 1) for i in s['ids']) and s['ids'] == sorted(set(s['ids'])))
        require(s['source_observed_at'] is None or number(s['source_observed_at']))
    require(sources['catalog'] == source(None, [], None, 'producer_contract', None, contract=MODEL))
    require(sources['storage']['tables'] == ['seed_schema', 'episodes', 'transitions', 'world_model_queue', 'semantic_memories'])
    require(sources['storage']['ids'] == [])
    for name in ('storage', 'prediction_window', 'errors'):
        require(sources[name]['source_observed_at'] == p['measured_at'])
    for name in ('observation', 'transition'): require(sources[name]['ids'] == [p['source_transition_id']])
    require(sources['runtime']['ids'] in ([], [1]) and len(sources['consolidation']['ids']) <= 1)
    require(all(i <= p['source_transition_id'] for name in ('prediction_window', 'prediction_coverage', 'prediction_score') for i in sources[name]['ids']))
    require(all(i <= p['source_event_id'] for i in sources['errors']['ids']))
    keys(p['observations'], SENSORS)
    keys(p['resources'], RESOURCES)
    keys(p['capabilities'], ('sensors', 'actions', 'unsupported'))
    keys(p['capabilities']['sensors'], SENSORS)
    keys(p['capabilities']['actions'], ACTIONS)
    keys(p['capabilities']['unsupported'], UNSUPPORTED)
    keys(p['prediction_performance'], ('window', 'coverage', 'score'))
    keys(p['memory'], ('storage', 'latest_consolidation', 'runtime_reported'))
    expected_sources = [(p['observations'][k], 'observation') for k in SENSORS]
    expected_sources += [(v, 'catalog') for group in ('actions', 'unsupported') for v in p['capabilities'][group].values()]
    expected_sources += [(p['last_selected_action'], 'transition'), (p['recent_failures'], 'errors')]
    expected_sources += [(v, 'prediction_' + k) for k, v in p['prediction_performance'].items()]
    expected_sources += [(p['memory'][k], src) for k, src in (('storage', 'storage'), ('latest_consolidation', 'consolidation'), ('runtime_reported', 'runtime'))]
    for f, src in expected_sources:
        keys(f, ('value', 'status', 'reason', 'source'))
        require(f['source'] == src and f['status'] in STATUSES and f['reason'] in REASONS)
        if f['status'] == 'available':
            require(f['value'] is not None and f['reason'] in (None, 'partial_window'))
            require(_age(copy.deepcopy(f), sources[src], p['measured_at'], p['measured_at'])['status'] == 'available')
        elif f['status'] == 'stale':
            require(f['value'] is not None and f['reason'] in ('source_expired', 'snapshot_expired'))
            probe = field(f['value'], src)
            require(_age(probe, sources[src], p['measured_at'], p['measured_at'])['status'] == 'stale')
        else:
            allowed = {
                'error': ('invalid_value', 'invalid_json', 'oversized_source', 'invalid_timestamp', 'clock_regression', 'invalid_evidence'),
                'unavailable': ('not_recorded', 'missing_timestamp', 'no_consolidation_run', 'missing_runtime'),
                'insufficient_evidence': ('no_supported_evaluations', 'no_scored_evaluations'),
                'not_supported': ('outside_action_contract',),
            }
            require(f['reason'] in allowed[f['status']])
    for name in SENSORS:
        require(p['capabilities']['sensors'][name] == dict(supported=True, reading='observations.' + name))
        require(p['capabilities']['sensors'][name]['supported'] is True)
        f = p['observations'][name]
        require(f['value'] is None or sensor_valid(name, f['value']))
        require(f['status'] in ('available', 'unavailable', 'stale', 'error'))
        if f['status'] in ('available', 'stale'):
            require(number(sources['observation']['source_observed_at'], 0,
                           sources['transition']['source_observed_at']))
    for name in RESOURCES: require(p['resources'][name] == 'observations.' + name)
    for name, work in ACTIONS.items():
        require(all(p['capabilities']['actions'][name]['value'][k] is True for k in ('implemented', 'selectable', 'owner_controlled')))
        require(p['capabilities']['actions'][name] == field(dict(implemented=True, selectable=True, owner_controlled=True, work_kind=work), 'catalog'))
    for name in UNSUPPORTED:
        f = p['capabilities']['unsupported'][name]
        require(f['value'] is False and f == field(False, 'catalog', 'not_supported', 'outside_action_contract'))
    require(p['last_selected_action']['value'] in ACTIONS)
    w = p['prediction_performance']['window']['value']
    keys(w, ('raw_rows', 'raw_transition_ids', 'valid_evaluations', 'missing_evaluations', 'unsupported_evaluations', 'invalid_evaluations'))
    require(w['raw_transition_ids'] == sources['prediction_window']['ids'] and w['raw_rows'] == len(w['raw_transition_ids']))
    require(all(integer(w[k], 0, 100) for k in w if k != 'raw_transition_ids'))
    require(w['raw_rows'] == sum(w[k] for k in ('valid_evaluations', 'missing_evaluations', 'unsupported_evaluations', 'invalid_evaluations')))
    for k in ('oldest_completed_at', 'newest_completed_at'):
        require(sources['prediction_window'][k] is None or number(sources['prediction_window'][k], 0, p['measured_at']))
    for label in ('coverage', 'score'):
        f = p['prediction_performance'][label]
        v = f['value']
        metrics = ('mean',) if label == 'coverage' else ('mean_normalized_error', 'accuracy_score')
        keys(v, ('samples', *metrics))
        require(integer(v['samples'], 0, 100) and v['samples'] == len(sources['prediction_' + label]['ids']))
        require(set(sources['prediction_' + label]['ids']) <= set(w['raw_transition_ids']))
        if not v['samples']:
            require(all(v[k] is None for k in metrics) and f['status'] in ('error', 'insufficient_evidence'))
            require(sources['prediction_' + label]['source_observed_at'] is None)
        else:
            require(all(number(v[k], 0, 1) for k in metrics) and f['status'] in ('available', 'stale', 'error'))
            require(number(sources['prediction_' + label]['source_observed_at'], 0, p['measured_at']))
    c, s = (p['prediction_performance'][k]['value'] for k in ('coverage', 'score'))
    require(c['samples'] == w['valid_evaluations'] and s['samples'] <= c['samples'])
    require(set(sources['prediction_score']['ids']) <= set(sources['prediction_coverage']['ids']))
    if s['samples']: require(math.isclose(s['accuracy_score'], 1 - s['mean_normalized_error'], abs_tol=1e-12, rel_tol=0))
    storage = p['memory']['storage']['value']
    keys(storage, ('schema_version', 'bounded_reads_succeeded', 'page_size', 'page_count', 'logical_allocated_bytes', *COUNT_TABLES))
    require(type(storage['schema_version']) is int and storage['schema_version'] in (6, 7) and storage['bounded_reads_succeeded'] is True)
    require(integer(storage['page_size'], 1) and integer(storage['page_count']) and integer(storage['logical_allocated_bytes']))
    require(storage['logical_allocated_bytes'] == storage['page_size'] * storage['page_count'])
    for name in COUNT_TABLES:
        keys(storage[name], ('count', 'relation'))
        require(integer(storage[name]['count'], 0, 1001) and storage[name]['relation'] == ('at_least' if storage[name]['count'] == 1001 else 'exact'))
    run = p['memory']['latest_consolidation']['value']
    if run is not None:
        _valid_run(run)
        require(sources['consolidation']['ids'] == [run['run_id']])
        require(sources['consolidation']['source_observed_at'] == run[sources['consolidation']['timestamp_kind']])
        if p['memory']['latest_consolidation']['status'] in ('available', 'stale'):
            require(run['suppression_reason'] in ('high_load', 'low_battery', 'low_disk') if run['status'] == 'suppressed' else run['suppression_reason'] is None)
    runtime = p['memory']['runtime_reported']['value']
    if runtime is not None:
        require(sources['runtime']['ids'] == [1])
        keys(runtime, ('heartbeat', 'last_successful_cycle', 'session_id'))
        require(number(runtime['heartbeat']) and (runtime['last_successful_cycle'] is None or number(runtime['last_successful_cycle'])) and text(runtime['session_id']))
        require(runtime['heartbeat'] == sources['runtime']['source_observed_at'])
        if p['memory']['runtime_reported']['status'] in ('available', 'stale'):
            require(runtime['last_successful_cycle'] is None or runtime['last_successful_cycle'] <= p['measured_at'])
    f = p['recent_failures']['value']
    keys(f, ('count', 'has_older_retained_errors', 'oldest_event_id', 'newest_event_id', 'latest_valid_event', 'invalid_metadata_count'))
    ids = sources['errors']['ids']
    require(integer(f['count'], 0, 100) and f['count'] == len(ids) and type(f['has_older_retained_errors']) is bool)
    require(not f['has_older_retained_errors'] or f['count'] == 100)
    require(f['oldest_event_id'] == (ids[0] if ids else None) and f['newest_event_id'] == (ids[-1] if ids else None))
    require(integer(f['invalid_metadata_count'], 0, len(ids)))
    latest = f['latest_valid_event']
    if latest is not None:
        keys(latest, ('id', 'ts', 'category', 'source'))
        require(latest['id'] in ids and number(latest['ts'], 0, p['measured_at']) and latest['category'] == 'ERROR' and text(latest['source']))
    else:
        require(f['count'] == f['invalid_metadata_count'])
    failure_field = p['recent_failures']
    valid_count = f['count'] - f['invalid_metadata_count']
    require((latest is not None) == (valid_count > 0))
    if f['count'] and not valid_count:
        require(failure_field['status'] == 'error' and failure_field['reason'] == 'invalid_value')
    else:
        # At publication this source clock equals measured_at, so it cannot be stale.
        require(failure_field['status'] == 'available')
        require(failure_field['reason'] == ('partial_window' if f['invalid_metadata_count'] else None))
    # Also enforce global structural/byte bounds for callers supplying dictionaries.
    bounded_json(json.dumps(p, ensure_ascii=True, allow_nan=False), SNAPSHOT_BYTES)
    return p


def decode_snapshot(raw):
    p = bounded_json(raw, SNAPSHOT_BYTES)
    try:
        return validate_snapshot(p)
    except (KeyError, TypeError, OverflowError) as exc:
        raise ValueError('invalid_snapshot') from exc


def project_snapshot(payload, read_at):
    validate_snapshot(payload)
    require(number(read_at))
    p = copy.deepcopy(payload)
    for item in envelopes(p): _age(item, p['sources'][item['source']], p['measured_at'], read_at)
    return p


@contextmanager
def sql_budget(db, stop_event=None, operations=100000, cleanup_errors=None):
    """Scoped on a connection owned by this caller; no existing callback is installed."""
    ticks = 0
    def progress():
        nonlocal ticks
        ticks += 1000
        return int(ticks >= operations or stop_event is not None and stop_event.is_set())
    db.set_progress_handler(progress, 1000)
    try:
        yield
    finally:
        try:
            db.set_progress_handler(None, 0)
        except Exception:
            if cleanup_errors is None:
                raise
            cleanup_errors.append('progress_handler')


def _read_evidence(db, tid):
    versions = db.execute('SELECT version FROM seed_schema LIMIT 2').fetchall()
    require(len(versions) == 1 and type(versions[0][0]) is int and versions[0][0] in (6, 7))
    row = db.execute('''SELECT id,started_at,completed_at,substr(CAST(action AS BLOB),1,129) AS action,
        substr(CAST(state_after_json AS BLOB),1,16385) AS state FROM transitions WHERE id=?''', (tid,)).fetchone()
    evaluations = db.execute('''SELECT id,started_at,completed_at,
        substr(CAST(prediction_error_json AS BLOB),1,16385) AS evaluation
        FROM transitions WHERE id<=? ORDER BY id DESC LIMIT 100''', (tid,)).fetchall()
    cutoff = db.execute('SELECT id FROM events ORDER BY id DESC LIMIT 1').fetchone()
    cutoff = cutoff[0] if cutoff else 0
    errors = db.execute('''SELECT id,ts,substr(CAST(source AS BLOB),1,129) AS source FROM events
        WHERE category='ERROR' AND id<=? ORDER BY id DESC LIMIT 101''', (cutoff,)).fetchall()
    counts = {key: db.execute(f'SELECT {pk} FROM {table} ORDER BY {pk} LIMIT 1001').fetchall()
              for key, (table, pk) in COUNT_TABLES.items()}
    columns = ','.join(RUN_COUNTS)
    run = db.execute(f'''SELECT id,started_at,completed_at,model_version,{columns},
        substr(CAST(model AS BLOB),1,129) AS model,substr(CAST(status AS BLOB),1,129) AS status,
        substr(CAST(provenance AS BLOB),1,129) AS provenance,substr(CAST(result_json AS BLOB),1,16385) AS result
        FROM consolidation_runs ORDER BY id DESC LIMIT 1''').fetchone()
    runtime = db.execute('SELECT substr(CAST(data_json AS BLOB),1,16385) AS data FROM runtime WHERE singleton=1').fetchone()
    return dict(schema_version=versions[0][0], transition=row, evaluations=evaluations, event_cutoff=cutoff, errors=errors, counts=counts,
                consolidation=run, runtime=runtime, page_size=db.execute('PRAGMA page_size').fetchone()[0],
                page_count=db.execute('PRAGMA page_count').fetchone()[0])


class SelfModel:
    def __init__(self, memory, clock=time.time):
        self.memory, self.clock = memory, clock

    def update(self, transition_id, session_id, stop_event):
        if stop_event.is_set() or not self.memory._lock.acquire(blocking=False):
            return 'skipped'
        db = self.memory.db
        timeout = None
        configured = owned = False
        result, failure_reason = 'skipped', None
        cleanup_errors = []
        try:
            if stop_event.is_set() or db.in_transaction:
                return 'skipped'
            require(integer(transition_id, 1) and text(session_id))
            timeout = db.execute('PRAGMA busy_timeout').fetchone()[0]
            db.execute('PRAGMA busy_timeout=0')
            configured = True
            with sql_budget(db, stop_event, cleanup_errors=cleanup_errors):
                db.execute('BEGIN IMMEDIATE')
                owned = True
                prior = db.execute('SELECT source_transition_id FROM self_model_current WHERE singleton=1').fetchone()
                if not (prior and integer(prior[0], 1) and prior[0] >= transition_id):
                    p = build_snapshot(_read_evidence(db, transition_id), self.clock(), transition_id, session_id)
                    raw = json.dumps(p, ensure_ascii=True, allow_nan=False, separators=(',', ':'))
                    summary = dict(model=MODEL, model_version=1, source_transition_id=transition_id, status='updated',
                        field_status_counts=dict(Counter({s: 0 for s in STATUSES}) + Counter(f['status'] for f in envelopes(p))),
                        prediction_sample_count=p['prediction_performance']['score']['value']['samples'],
                        recent_failure_count=p['recent_failures']['value']['count'], source_event_id=p['source_event_id'])
                    summary['field_status_counts'] = {s: summary['field_status_counts'].get(s, 0) for s in STATUSES}
                    require(len(json.dumps(summary).encode()) <= 1024)
                    db.execute('''INSERT INTO self_model_current VALUES(1,?,?,?,?,?) ON CONFLICT(singleton) DO UPDATE SET
                        updated_at=excluded.updated_at,model=excluded.model,model_version=excluded.model_version,
                        source_transition_id=excluded.source_transition_id,data_json=excluded.data_json''',
                        (p['measured_at'], MODEL, MODEL_VERSION, transition_id, raw))
                    emit(db, 'SELF_MODEL', 'self_model', 'Self model snapshot updated', summary)
                    if not stop_event.is_set():
                        db.commit()
                        owned = False
                        result = 'updated'
        except Exception as exc:
            result = 'skipped' if stop_event.is_set() else 'failed'
            failure_reason = 'storage_failed' if isinstance(exc, sqlite3.Error) else 'invalid_snapshot'
        finally:
            # Each cleanup is independent. A failed rollback or handler removal leaves
            # ownership uncertain: log only, without attempting a diagnostic transaction.
            try:
                try:
                    if owned:
                        try:
                            db.rollback()
                        except Exception:
                            cleanup_errors.append('rollback')
                    if failure_reason and not stop_event.is_set():
                        if configured and not cleanup_errors:
                            self._failure(transition_id, failure_reason, cleanup_errors)
                        else:
                            log.warning('Self model update failed; durable diagnostic unavailable')
                finally:
                    if timeout is not None:
                        try:
                            db.execute(f'PRAGMA busy_timeout={int(timeout)}')
                        except Exception:
                            cleanup_errors.append('busy_timeout')
                    if cleanup_errors:
                        log.warning('Self model cleanup failed; connection state may be unusable')
            finally:
                self.memory._lock.release()
        return 'failed' if cleanup_errors else result

    def _failure(self, transition_id, reason, cleanup_errors):
        db = self.memory.db
        owned = False
        try:
            if db.in_transaction:
                return
            with sql_budget(db, operations=2000, cleanup_errors=cleanup_errors):
                db.execute('BEGIN IMMEDIATE')
                owned = True
                emit(db, 'SELF_MODEL', 'self_model', 'Self model update failed',
                     dict(model=MODEL, model_version=1, source_transition_id=transition_id if integer(transition_id, 1) else None,
                          status='failed', reason=reason))
                db.commit()
                owned = False
        except Exception:
            log.warning('Self model update failed; durable diagnostic unavailable')
        finally:
            if owned:
                try:
                    db.rollback()
                except Exception:
                    cleanup_errors.append('diagnostic_rollback')
