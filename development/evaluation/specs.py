"""Strict registered experiment admission only; no execution or scenarios."""
import json
import re
from .contracts import ContractError, ExperimentSpec, fields, strict_json, validate_json
from .registry import lookup, PROTOCOLS

# Binding admission ceilings shared with the later incremental enforcers.
CAPS = {'transitions': 1024, 'training': 512, 'measured': 1024, 'attempts': 2048, 'skips': 8,
        'seeds': 8, 'runs': 32, 'run_seconds': 120, 'suite_seconds': 1800, 'ack_seconds': 10,
        'cleanup_seconds': 5, 'worker_bytes': 512*1024**2, 'coordinator_bytes': 512*1024**2,
        'logical_db_bytes': 32*1024**2, 'physical_db_bytes': 64*1024**2, 'clone_slots': 2,
        'workspace_bytes': 128*1024**2, 'detail_bytes': 64*1024, 'snapshot_bytes': 128*1024**2,
        'control_bytes': 4*1024**2, 'operational_bytes': 4*1024**2, 'artifact_bytes': 224*1024**2,
        'artifact_files': 32, 'reservation_bytes': 448*1024**2, 'root_bytes': 16*1024**3,
        'retained_runs': 60, 'plan_bytes': 128*1024, 'metrics_bytes': 256*1024,
        'baseline_methods': 2}


def identifier(value):
    if type(value) is not str or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}', value):
        raise ContractError()
    return value


def integer(value, low=1, high=2**31-1):
    if type(value) is not int or not low <= value <= high:
        raise ContractError()
    return value


def digest(value, length=64):
    if type(value) is not str or not re.fullmatch('[0-9a-f]{' + str(length) + '}', value):
        raise ContractError()


def versions(values, kind, maximum=33):
    if type(values) is not list or not 1 <= len(values) <= maximum:
        raise ContractError()
    seen = set()
    for item in values:
        fields(item, ('id', 'version'))
        lookup(item['id'], item['version'], kind=kind)
        if item['id'] in seen:
            raise ContractError()
        seen.add(item['id'])


def seeds(values):
    if type(values) is not list or not 1 <= len(values) <= 8 or len(set(values)) != len(values):
        raise ContractError()
    for value in values:
        integer(value, 0, 2**63-1)


def windows(values):
    if type(values) is not list or not values:
        raise ContractError()
    seen = set()
    for window in values:
        fields(window, ('id', 'start', 'end', 'unit'))
        identifier(window['id'])
        integer(window['start'], 1, 1024)
        integer(window['end'], window['start'], 1024)
        if window['unit'] not in ('ordinal', 'exposure') or window['id'] in seen:
            raise ContractError()
        seen.add(window['id'])


def limits(values):
    if type(values) is not dict or values.keys() - CAPS.keys():
        raise ContractError()
    for key, value in values.items():
        integer(value, 1, CAPS[key])


def raw_bytes(value):
    validate_json(value)
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')


def validate_spec(raw) -> ExperimentSpec:
    validate_json(raw)
    fields(raw, ('schema', 'experiment_id', 'version', 'family', 'scenario_version', 'rule_version',
                 'protocol', 'driver', 'source_commit', 'lock_digest', 'profile_digest', 'fixture',
                 'fixture_digest', 'seeds', 'rng', 'training', 'measured', 'clock', 'windows', 'metrics',
                 'baselines', 'variant', 'maintenance', 'observation_version', 'action_version', 'limits'))
    if raw['schema'] != 'b10_experiment_v1':
        raise ContractError()
    identifier(raw['experiment_id'])
    integer(raw['version'])
    lookup(raw['family'], raw['scenario_version'], kind='family')
    if raw['rule_version'] != raw['scenario_version'] or type(raw['rule_version']) is not int:
        raise ContractError()
    for key, size in [('source_commit', 40), ('lock_digest', 64), ('profile_digest', 64), ('fixture_digest', 64)]:
        digest(raw[key], size)
    seeds(raw['seeds'])
    integer(raw['training'], 0, 512)
    integer(raw['measured'], 1, 1024)
    if raw['training'] + raw['measured'] > 1024 or raw['protocol'] not in PROTOCOLS:
        raise ContractError()
    if raw['driver'] not in ('seed-cycle-v1', 'existing_cycle_adapter_v1', 'frozen_projection_v1', 'producer_fixture_v1'):
        raise ContractError()
    if raw['variant'] not in ('seed', 'random-eligible', 'fresh', 'contradictory', 'unavailable', 'stale'):
        raise ContractError()
    if raw['fixture'] not in ('fresh-v7', 'producer-v7') or raw['rng'] != 'sha256-mt19937-v1' or raw['clock'] != 'staged-v1':
        raise ContractError()
    if raw['maintenance'] not in ('every-eight', 'none') or type(raw['observation_version']) is not int or raw['observation_version'] != 1 or type(raw['action_version']) is not int or raw['action_version'] != 1:
        raise ContractError()
    versions(raw['metrics'], 'metric')
    versions(raw['baselines'], 'baseline', 2)
    windows(raw['windows'])
    limits(raw['limits'])
    lowered = raw['limits']
    if (raw['training'] > lowered.get('training', 512) or raw['measured'] > lowered.get('measured', 1024)
            or raw['training'] + raw['measured'] > lowered.get('transitions', 1024)
            or len(raw['seeds']) > lowered.get('seeds', 8)):
        raise ContractError()
    body = raw_bytes(raw)
    if len(body) > 128*1024:
        raise ContractError()
    return ExperimentSpec(body)


def require_plan(spec, plan):
    s = strict_json(spec.body, max_bytes=128*1024)
    p = strict_json(plan.body, max_bytes=128*1024)
    for sk, pk in [('experiment_id', 'experiment_id'), ('version', 'experiment_version'),
                   ('seeds', 'seeds'), ('metrics', 'metrics'), ('windows', 'windows'), ('baselines', 'baselines')]:
        if raw_bytes(s[sk]) != raw_bytes(p[pk]):
            raise ContractError()
    matching = [m for m in p['members'] if m['family'] == s['family'] and m['protocol'] == s['protocol'] and m['variant'] == s['variant']]
    if not matching or {m['seed'] for m in matching} != set(s['seeds']):
        raise ContractError()
    for m in matching:
        if any(m[k] != s[k] for k in ('scenario_version', 'rule_version', 'training', 'measured')):
            raise ContractError()
