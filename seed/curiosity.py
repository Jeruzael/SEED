"""Bounded computational salience; assessments grant no capabilities."""
import json
import math
from . import world_model as world

MODEL = 'curiosity_v1'
MODEL_VERSION = 1


def _unit(value):
    return type(value) in (int, float) and 0 <= value <= 1 and math.isfinite(value)


def attention_suppression(assessment, action, after):
    """Static guards only. A score is independent of attention eligibility."""
    if assessment['status'] != 'evaluated':
        return 'unavailable_evaluation'
    if assessment['level'] not in ('HIGH', 'VERY_HIGH'):
        return 'below_threshold'
    if not _unit(assessment['coverage']) or assessment['coverage'] < .5:
        return 'insufficient_coverage'
    if action == 'reflect':
        return 'already_reflected'
    after = after if isinstance(after, dict) else {}
    load = world._number(after.get('load_ratio'), 'load_ratio')
    battery = world._number(after.get('battery_pct'), 'battery_pct')
    disk = world._number(after.get('disk_free_pct'), 'disk_free_pct')
    if load is not None and load > .8:
        return 'high_load'
    if battery is not None and battery < 20 and after.get('charging') is False:
        return 'low_battery'
    if disk is not None and disk < 10:
        return 'low_disk'
    return None


def assess_curiosity(evaluation, before, action, after, prior_beliefs):
    """Pure assessment from original B3 error and a detached prior B4 snapshot.

    Uncertainty means lack of established consistent evidence, not probability of
    falsehood. Half-offset modifiers retain meaningful error when either is zero.
    """
    result = dict(model=MODEL, model_version=MODEL_VERSION, status='unavailable',
                  score=None, level='UNAVAILABLE', prediction_surprise=None,
                  uncertainty=None, novelty=None, coverage=None, components={'signals': {}},
                  reflection_eligible=False, suppression_reason='unavailable_evaluation')
    if (not isinstance(evaluation, dict) or evaluation.get('evaluator') != 'prediction_error_v1' or
        type(evaluation.get('evaluator_version')) is not int or evaluation['evaluator_version'] != 1):
        return result
    aggregate = evaluation.get('aggregate')
    if not isinstance(aggregate, dict) or aggregate.get('status') != 'evaluated':
        return result
    error, coverage = aggregate.get('mean_normalized_error'), aggregate.get('coverage')
    if not _unit(error) or not _unit(coverage) or coverage == 0:
        return result
    samples = world.transition_samples(before, action, after)
    if not samples:
        return result
    for signal, sample in samples.items():
        prior = prior_beliefs.get(signal)
        contradictory = world.contradicts(signal, sample, prior)
        uncertainty = max(0., min(1., 1 - prior['confidence'])) if prior else 1.
        novelty = 1. if prior is None else (.5 if prior['evidence_count'] < 4 else float(contradictory))
        snapshot = None
        if prior is not None:
            snapshot = {key: prior[key] for key in ('belief_key', 'scope', 'scope_value',
                         'evidence_count', 'confidence', 'source_last_transition_id')}
            snapshot['value'] = json.loads(prior['value_json'])
        result['components']['signals'][signal] = dict(sample=sample, prior_belief=snapshot,
            uncertainty=uncertainty, novelty=novelty, contradictory=contradictory)
    parts = result['components']['signals'].values()
    uncertainty = math.fsum(p['uncertainty'] for p in parts) / len(samples)
    novelty = math.fsum(p['novelty'] for p in parts) / len(samples)
    surprise = error * coverage
    score = max(0., min(1., surprise * (.5 + .5 * uncertainty) * (.5 + .5 * novelty)))
    level = 'LOW' if score < .2 else 'NOTABLE' if score < .5 else 'HIGH' if score < .75 else 'VERY_HIGH'
    result.update(status='evaluated', score=score, level=level, prediction_surprise=surprise,
                  uncertainty=uncertainty, novelty=novelty, coverage=coverage)
    reason = attention_suppression(result, action, after)
    result.update(reflection_eligible=reason is None, suppression_reason=reason)
    return result
