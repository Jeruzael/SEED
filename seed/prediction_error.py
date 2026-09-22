"""Versioned, pure scoring of prospective predictions; never a policy input."""
from dataclasses import asdict, dataclass
import json
import math

TARGETS = ('battery_pct', 'load_ratio', 'disk_free_pct', 'network_reachable')
MAX_JSON_CHARACTERS = 16384


@dataclass(frozen=True)
class PredictionEvaluation:
    signals: dict
    aggregate: dict
    prediction_model: str | None
    prediction_model_version: int | None
    horizon: str | None
    evaluator: str = 'prediction_error_v1'
    evaluator_version: int = 1

    def to_dict(self) -> dict:
        return asdict(self)


def _payload(value):
    if isinstance(value, str):
        if len(value) > MAX_JSON_CHARACTERS:
            return {}
        try:
            value = json.loads(value)
        except (ValueError, TypeError, RecursionError):
            return {}
    return value if isinstance(value, dict) else {}


def _number(value, upper=None):
    # These validation rules belong to evaluator v1, independently of future models.
    if type(value) not in (int, float):
        return None
    try:
        value = float(value)
    except OverflowError:
        return None
    if not math.isfinite(value) or value < 0 or (upper is not None and value > upper):
        return None
    return value


def _unavailable(reason):
    return {'status': 'not_evaluated', 'reason': reason}


def _evaluate_signal(target, prediction, actual):
    if not isinstance(prediction, dict):
        return _unavailable('invalid_prediction')
    if prediction.get('status') == 'unavailable':
        return _unavailable('prediction_unavailable')
    if prediction.get('status') != 'predicted':
        return _unavailable('invalid_prediction')
    expected = prediction.get('value')
    if target == 'network_reachable':
        if type(expected) is not bool:
            return _unavailable('invalid_prediction')
        if type(actual) is not bool:
            return _unavailable('actual_unavailable')
        correct = expected == actual
        mismatch = 0 if correct else 1
        result = {'status': 'evaluated', 'predicted': expected, 'actual': actual,
                  'correct': correct, 'classification_error': mismatch,
                  'normalized_error': mismatch, 'scoring_method': 'boolean_mismatch'}
        probability = _number(prediction.get('probability_true'), 1)
        if probability is not None:
            brier = (probability - int(actual)) ** 2
            result.update(probability_true=probability, brier_error=brier,
                          normalized_error=brier, scoring_method='boolean_brier')
        return result

    upper = None if target == 'load_ratio' else 100
    expected, actual = _number(expected, upper), _number(actual, upper)
    if expected is None:
        return _unavailable('invalid_prediction')
    if actual is None:
        return _unavailable('actual_unavailable')
    signed = actual - expected
    absolute = abs(signed)
    denominator = max(1.0, abs(expected), abs(actual)) if upper is None else 100
    normalized = absolute / denominator
    if not all(math.isfinite(value) for value in (signed, absolute, normalized)):
        return _unavailable('nonfinite_calculation')
    return {'status': 'evaluated', 'predicted': expected, 'actual': actual,
            'signed_error': signed, 'absolute_error': absolute,
            'normalized_error': min(1.0, max(0.0, normalized)),
            'scoring_method': 'bounded_relative' if upper is None else 'percentage_range'}


def evaluate_prediction(prediction, actual_state) -> PredictionEvaluation:
    """Score four targets only. No history, sensing, mutation, or prediction generation."""
    prediction = _payload(prediction)
    valid = (prediction.get('model') == 'transition_delta_v1'
             and type(prediction.get('model_version')) is int and prediction['model_version'] == 1
             and prediction.get('horizon') == 'next_post_action_observation'
             and isinstance(prediction.get('signals'), dict))
    predictions = prediction['signals'] if valid else {}
    actual = actual_state if isinstance(actual_state, dict) else {}
    signals = {target: _evaluate_signal(target, predictions.get(target),
                                       actual.get('network' if target == 'network_reachable' else target))
               for target in TARGETS}
    errors = [signal['normalized_error'] for signal in signals.values() if signal['status'] == 'evaluated']
    mean = min(1.0, max(0.0, math.fsum(errors) / len(errors))) if errors else None
    aggregate = {'status': 'evaluated' if errors else 'unavailable',
                 'evaluated_signals': len(errors), 'target_signals': len(TARGETS),
                 'coverage': len(errors) / len(TARGETS), 'mean_normalized_error': mean,
                 'accuracy_score': min(1.0, max(0.0, 1 - mean)) if mean is not None else None}
    return PredictionEvaluation(signals=signals, aggregate=aggregate,
                                prediction_model=prediction['model'] if valid else None,
                                prediction_model_version=prediction['model_version'] if valid else None,
                                horizon=prediction['horizon'] if valid else None)
