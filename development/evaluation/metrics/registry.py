"""Versioned measurements bound to an admitted frozen AnalysisPlan."""
import hashlib
from ..analysis import analysis_digest, validate_plan
from ..canonical import canonical_bytes
from ..contracts import ContractError, FrozenPlan, Measurement, Population, strict_json
from ..registry import METRICS, REGISTRIES
from ..specs import raw_bytes


def plan_data(plan):
    if type(plan) is not FrozenPlan:
        raise ContractError()
    body = strict_json(plan.plan.body, max_bytes=128*1024)
    validate_plan(body)
    receipt = strict_json(plan.receipt)
    if (analysis_digest(plan.plan) != plan.digest or receipt.get('digest') != plan.digest
            or receipt.get('frozen_before_execution') is not True
            or receipt.get('body_sha256') != hashlib.sha256(canonical_bytes(body)).hexdigest()):
        raise ContractError()
    return body


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
    dimensions = dict(family=member['family'], protocol=member['protocol'], seed=member['seed'],
        population=definition['id'], window=window['id'], phase=definition['phase'],
        action=definition['action'], signal=definition['signal'], method=definition.get('method','seed'),
        comparison=definition.get('comparison'), stratum=definition.get('stratum','all_methods'))
    return identity, version, member, definition, window, dimensions


def measured(metric, population, plan, *, value=None, reason=None, state=None, **facts):
    identity, version, member, definition, window, dimensions = resolve(metric, population, plan)
    state = state or ('MEASURED' if value is not None else 'UNAVAILABLE')
    if state not in ('MEASURED','UNAVAILABLE','NOT_EVALUATED') or ((value is None) != (state != 'MEASURED')):
        raise ContractError()
    if state != 'MEASURED' and not reason:
        raise ContractError()
    body = raw_bytes(dict(value=value, reason=reason, plan_digest=plan.digest, dimensions=dimensions, **facts))
    if len(body) > 65536:
        raise ContractError()
    return Measurement(identity, metric, version, member['id'], state, body)


def measurement_data(measurement):
    if type(measurement) is not Measurement:
        raise ContractError()
    return strict_json(measurement.body)
