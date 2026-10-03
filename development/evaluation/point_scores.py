"""Literal, single-transition losses. No aggregate or learner feedback API."""
import math
from .contracts import ContractError, PreUpdateEvidence, decode_message


def brier(probability_true, outcome):
    if (type(probability_true) not in (int, float) or not math.isfinite(probability_true)
            or not 0 <= probability_true <= 1 or type(outcome) is not bool):
        raise ContractError()
    return (probability_true - int(outcome)) ** 2


def point_scores(evidence: PreUpdateEvidence):
    if type(evidence) is not PreUpdateEvidence:
        raise ContractError()
    value = decode_message(evidence.body, 'checkpoint')
    result = {}
    for target in ('battery_pct', 'load_ratio', 'disk_free_pct', 'network_reachable'):
        signal = value['prediction']['signals'][target]
        observed = value['state_after'].get('network' if target == 'network_reachable' else target)
        reason = ('prediction_unavailable' if signal['status'] == 'unavailable' else
                  'outcome_unavailable' if observed is None else None)
        entry = dict(status='unavailable' if reason else 'scored', unavailable_reason=reason)
        if target != 'network_reachable':
            loss = None if reason else abs(signal['value'] - observed)
            if loss is not None and not math.isfinite(loss):
                raise ContractError()
            entry['absolute_error'] = loss
        else:
            entry['correct'] = None if reason else signal['value'] == observed
            probability = signal.get('probability_true')
            brier_reason = reason or ('probability_unavailable' if probability is None else None)
            entry.update(brier_status='unavailable' if brier_reason else 'scored',
                         brier=None if brier_reason else brier(probability, observed),
                         brier_unavailable_reason=brier_reason)
        result[target] = entry
    return result
