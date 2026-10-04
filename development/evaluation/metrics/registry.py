"""Versioned measurements bound to an admitted frozen AnalysisPlan."""
import hashlib
from functools import lru_cache
from ..analysis import analysis_digest, validate_plan, expand_inventory, inventory_metadata
from ..canonical import canonical_bytes
from ..contracts import ContractError, FrozenPlan, Measurement, Population, strict_json
from ..registry import METRICS, REGISTRIES
from ..specs import raw_bytes


@lru_cache(maxsize=16)
def _admitted(plan):
    if type(plan) is not FrozenPlan:
        raise ContractError()
    body = strict_json(plan.plan.body, max_bytes=128*1024)
    validate_plan(body)
    receipt = strict_json(plan.receipt)
    if (analysis_digest(plan.plan) != plan.digest or receipt.get('digest') != plan.digest
            or receipt.get('frozen_before_execution') is not True
            or receipt.get('body_sha256') != hashlib.sha256(canonical_bytes(body)).hexdigest()):
        raise ContractError()
    if (receipt.get('schema')!='b10_plan_freeze_v1'
            or receipt.get('identity')!=body['experiment_id']+'-'+str(body['experiment_version'])+'-'+str(body['analysis_plan_version'])
            or receipt.get('first_members')!=[[m['id'],'training' if m['training'] else 'measured',1] for m in body['members']]):
        raise ContractError()
    return plan.plan.body


def plan_data(plan):
    # Cache immutable admitted bytes, never a mutable dictionary shared with a caller.
    return strict_json(_admitted(plan),max_bytes=128*1024)


@lru_cache(maxsize=16)
def _inventory(plan):
    _admitted(plan)
    return {row.identity:row for row in expand_inventory(plan.plan)}


def expected_metadata(plan,row):
    expected=_inventory(plan).get(row.identity)
    if expected is None or (row.metric,row.version,row.member,row.role)!=(expected.metric,expected.version,expected.member,expected.role):
        raise ContractError()
    return strict_json(expected.body)


def resolve(metric, population, plan):
    body = plan_data(plan)
    if type(population) is not Population or len(population.members) != 1:
        raise ContractError()
    member = next((m for m in body['members'] if m['id'] == population.members[0]), None)
    definition = next((p for p in body['populations'] if p['id'] == population.identity), None)
    window = next((w for w in body['windows'] if w['id'] == population.window), None)
    version = next((m['version'] for m in body['metrics'] if m['id'] == metric), None)
    if member is None or definition is None or window is None or version != REGISTRIES['metric'].get(metric):
        raise ContractError()
    identity = ':'.join((member['id'], metric, definition['id'], window['id']))
    if population.role=='EXPLORATORY_DIAGNOSTIC':identity+='~exploratory'
    expected=_inventory(plan).get(identity)
    if expected is None or population.role!=expected.role:
        raise ContractError()
    dimensions = inventory_metadata(member,metric,definition,window,population.role)['dimensions']
    return identity, version, member, definition, window, dimensions


def measured(metric, population, plan, *, value=None, reason=None, state=None, **facts):
    identity, version, member, definition, window, dimensions = resolve(metric, population, plan)
    state = state or ('MEASURED' if value is not None else 'UNAVAILABLE')
    meta=expected_metadata(plan,Measurement(identity,metric,version,member['id'],role=population.role))
    if not meta['applicable']:
        state,value,reason='NOT_EVALUATED',None,meta['reason']
    if state not in ('MEASURED','UNAVAILABLE','NOT_EVALUATED') or ((value is None) != (state != 'MEASURED')):
        raise ContractError()
    if state != 'MEASURED' and not reason:
        raise ContractError()
    body = raw_bytes(dict(value=value, reason=reason, plan_digest=plan.digest, dimensions=dimensions,
                         non_inferential=population.role=='EXPLORATORY_DIAGNOSTIC',**facts))
    if len(body) > 65536:
        raise ContractError()
    return Measurement(identity, metric, version, member['id'], state, body,population.role)


def measurement_data(measurement):
    if type(measurement) is not Measurement:
        raise ContractError()
    return strict_json(measurement.body)
