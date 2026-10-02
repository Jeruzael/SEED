"""Immutable plan admission and durable freeze. Scientific dispatch disabled."""
import hashlib
import os
from .canonical import canonical_bytes
from .contracts import AnalysisPlan, FrozenPlan, Measurement, ContractError, fields, strict_json, validate_json
from .registry import lookup, PROTOCOLS
from .specs import identifier, integer, versions, seeds, windows, raw_bytes

PLAN_FIELDS = ('schema', 'experiment_id', 'experiment_version', 'analysis_plan_version', 'members',
               'metrics', 'seeds', 'populations', 'windows', 'baselines', 'exclusions', 'eligibility',
               'coverage', 'aggregation', 'standardization', 'missing_rules', 'thresholds', 'questions', 'exploratory')


def validate_plan(raw) -> AnalysisPlan:
    validate_json(raw)
    fields(raw, PLAN_FIELDS)
    if raw['schema'] != 'b10_analysis_plan_v1':
        raise ContractError()
    identifier(raw['experiment_id'])
    integer(raw['experiment_version'])
    integer(raw['analysis_plan_version'])
    seeds(raw['seeds'])
    versions(raw['metrics'], 'metric')
    versions(raw['baselines'], 'baseline', 2)
    windows(raw['windows'])
    if type(raw['members']) is not list or not 1 <= len(raw['members']) <= 32:
        raise ContractError()
    seen = set()
    for m in raw['members']:
        fields(m, ('id', 'family', 'scenario_version', 'rule_version', 'protocol', 'variant', 'seed', 'training', 'measured'))
        identifier(m['id'])
        lookup(m['family'], m['scenario_version'], kind='family')
        integer(m['rule_version'])
        integer(m['seed'], 0, 2**63-1)
        integer(m['training'], 0, 512)
        integer(m['measured'], 1, 1024)
        if (m['id'] in seen or m['seed'] not in raw['seeds'] or m['rule_version'] != m['scenario_version']
                or m['training'] + m['measured'] > 1024 or m['protocol'] not in PROTOCOLS
                or m['variant'] not in ('seed', 'random-eligible', 'fresh', 'contradictory', 'unavailable', 'stale')):
            raise ContractError()
        seen.add(m['id'])
    if type(raw['populations']) is not list or not raw['populations']:
        raise ContractError()
    ids = set()
    for p in raw['populations']:
        fields(p, ('id', 'phase', 'action', 'signal'))
        identifier(p['id'])
        if p['id'] in ids or p['phase'] not in ('training', 'measured', 'probe') or p['action'] not in ('all', 'observe', 'reflect', 'consolidate', 'rest') or p['signal'] not in ('all', 'battery_pct', 'load_ratio', 'disk_free_pct', 'network'):
            raise ContractError()
        ids.add(p['id'])
    fixed = {'eligibility': 'registered_support', 'coverage': 'all_opportunities', 'aggregation': 'ordered_fsum',
             'standardization': 'equal_qualifying_actions', 'missing_rules': 'unavailable_with_reason'}
    if any(raw[k] != v for k, v in fixed.items()) or type(raw['exploratory']) is not bool:
        raise ContractError()
    if type(raw['exclusions']) is not list or any(v not in ('invalid_observation', 'insufficient_support', 'not_applicable') for v in raw['exclusions']):
        raise ContractError()
    if type(raw['thresholds']) is not list or type(raw['questions']) is not list or not raw['questions']:
        raise ContractError()
    tids = set()
    for t in raw['thresholds']:
        fields(t, ('id', 'version', 'value', 'metric', 'metric_version', 'population', 'direction', 'role', 'rationale', 'missing_rule'))
        identifier(t['id'])
        integer(t['version'])
        lookup(t['metric'], t['metric_version'], kind='metric')
        if (t['id'] in tids or type(t['value']) not in (int, float) or t['population'] not in ids
                or t['direction'] not in ('le', 'ge', 'eq') or t['role'] not in ('eligibility', 'event', 'engineering', 'classification')
                or type(t['rationale']) is not str or not t['rationale'] or t['missing_rule'] not in ('unavailable', 'inconclusive')):
            raise ContractError()
        tids.add(t['id'])
    qids = set()
    for q in raw['questions']:
        fields(q, ('id', 'metrics', 'rule', 'reason'))
        identifier(q['id'])
        if q['id'] in qids or type(q['metrics']) is not list or not q['metrics'] or len(set(q['metrics'])) != len(q['metrics']) or set(q['metrics']) - {m['id'] for m in raw['metrics']}:
            raise ContractError()
        # No classification executor belongs in this foundation PR.
        if q['rule'] != 'descriptive_only' or q['reason'] != 'DESCRIPTIVE_ONLY_NO_CLASSIFICATION_RULE':
            raise ContractError()
        qids.add(q['id'])
    body = raw_bytes(raw)
    if len(canonical_bytes(raw)) > 128*1024:
        raise ContractError()
    plan = AnalysisPlan(body)
    expand_inventory(plan)
    return plan


def expand_inventory(plan):
    p = strict_json(plan.body, max_bytes=128*1024)
    results = []
    # Budget admission precedes the allocation of each inventory row.
    for member in p['members']:
        byte_count = 2
        member_count = 0
        for metric in p['metrics']:
            for population in p['populations']:
                for window in p['windows']:
                    identity = ':'.join([member['id'], metric['id'], population['id'], window['id']])
                    row = Measurement(identity, metric['id'], metric['version'], member['id'])
                    byte_count += len(raw_bytes({'id':identity,'metric':row.metric,'version':row.version,'member':row.member,
                                                'state':'UNAVAILABLE','value':None,'reason':'INSUFFICIENT_EVIDENCE',
                                                'population':population['id'],'window':window['id']})) + 1
                    if byte_count > 256*1024 or member_count >= 4096:
                        raise ContractError()
                    results.append(row)
                    member_count += 1
    # Attempt and plan/control inventories share the 4 MiB ceiling.
    if byte_count + len(plan.body) + 2048*512 > 4*1024**2:
        raise ContractError()
    return tuple(results)


def analysis_digest(plan):
    return hashlib.sha256(b'SEED_B10_ANALYSIS_PLAN_V1\0' + canonical_bytes(strict_json(plan.body, max_bytes=128*1024))).hexdigest()


def _identity(plan):
    p = strict_json(plan.body, max_bytes=128*1024)
    return p['experiment_id'] + '-' + str(p['experiment_version']) + '-' + str(p['analysis_plan_version'])


def _read(capability, kind, identity, maximum):
    fd = capability.open(kind, identity, 'read')
    with os.fdopen(fd, 'rb') as f:
        value = f.read(maximum + 1)
    if len(value) > maximum:
        raise ContractError()
    return value


def freeze_plan(plan, capability):
    p = validate_plan(strict_json(plan.body, max_bytes=128*1024))
    digest = analysis_digest(p)
    body = canonical_bytes(strict_json(p.body, max_bytes=128*1024))
    receipt = raw_bytes({'schema':'b10_plan_freeze_v1','digest':digest,'body_sha256':hashlib.sha256(body).hexdigest(),
                        'identity':_identity(p),'frozen_before_execution':True,
                        'first_members':[[m['id'],'training' if m['training'] else 'measured',1]
                                         for m in strict_json(p.body, max_bytes=128*1024)['members']]})
    try:
        # Reserve the immutable version identity first, but never expose a valid
        # receipt until the body and directory entry have been fsynced.
        receipt_fd = capability.open('freeze', _identity(p), 'create')
        with os.fdopen(receipt_fd, 'wb') as out:
            body_fd = capability.open('plan', digest, 'create')
            with os.fdopen(body_fd, 'wb') as f:
                f.write(body)
                f.flush()
                os.fsync(f.fileno())
            capability.sync()
            out.write(receipt)
            out.flush()
            os.fsync(out.fileno())
        capability.sync()
        return FrozenPlan(p, digest, receipt)
    except OSError:
        raise ContractError() from None


def require_frozen(plan, capability):
    p = validate_plan(strict_json(plan.body, max_bytes=128*1024))
    digest = analysis_digest(p)
    try:
        raw = _read(capability, 'freeze', _identity(p), 16*1024)
        receipt = strict_json(raw, max_bytes=16*1024)
        fields(receipt, ('schema','digest','body_sha256','identity','frozen_before_execution','first_members'))
        body = _read(capability, 'plan', digest, 128*1024)
        expected = canonical_bytes(strict_json(p.body, max_bytes=128*1024))
        if (receipt['schema'] != 'b10_plan_freeze_v1' or receipt['identity'] != _identity(p) or receipt['digest'] != digest
                or receipt['frozen_before_execution'] is not True or body != expected
                or receipt['body_sha256'] != hashlib.sha256(body).hexdigest()
                or receipt['first_members'] != [[m['id'],'training' if m['training'] else 'measured',1]
                                               for m in strict_json(p.body, max_bytes=128*1024)['members']]):
            raise ContractError()
        return FrozenPlan(p, digest, raw)
    except OSError:
        raise ContractError() from None
