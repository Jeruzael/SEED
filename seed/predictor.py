"""Prospective immediate-outcome estimates; inference only, never policy or accuracy."""
from dataclasses import asdict, dataclass
import json
import math
import sys

HISTORY_LIMIT = 200
MIN_SAMPLES = 2
NUMERIC_TARGETS = ('battery_pct', 'load_ratio', 'disk_free_pct')


@dataclass(frozen=True)
class Prediction:
    action: str
    signals: dict
    model: str = 'transition_delta_v1'
    model_version: int = 1
    horizon: str = 'next_post_action_observation'

    def to_dict(self) -> dict:
        return asdict(self)


def _numeric(value, target):
    if type(value) not in (int, float):
        return None
    try:
        value = float(value)
    except OverflowError:
        return None
    if not math.isfinite(value) or value < 0:
        return None
    if target in ('battery_pct', 'disk_free_pct') and value > 100:
        return None
    return value


def _observation(payload):
    try:
        value = json.loads(payload)
    except (ValueError, TypeError, RecursionError):
        return None
    return value if isinstance(value, dict) else None


def _select_evidence(samples, action):
    matched = [value for selected, value in samples if selected == action]
    if len(matched) >= MIN_SAMPLES:
        return matched, 'action'
    if len(samples) >= MIN_SAMPLES:
        return [value for _, value in samples], 'global'
    return [], 'persistence'


def _support(count):
    return {'evidence_count': count, 'confidence': min(.95, count / 20),
            'confidence_kind': 'evidence_support'}


def _unavailable(state, key):
    return {'status': 'unavailable', 'reason': 'missing_current_value' if key not in state else 'invalid_current_value',
            **_support(0)}


class Predictor:
    def __init__(self, memory):
        self.memory = memory

    def predict(self, state_before: dict, action: str) -> Prediction:
        # Every persisted B1 transition is completed. Limit raw rows first, so
        # malformed history cannot cause an unbounded search for valid samples.
        with self.memory._lock:
            rows = self.memory.db.execute('''SELECT action,state_before_json,state_after_json
                FROM transitions ORDER BY id DESC LIMIT ?''', (HISTORY_LIMIT,)).fetchall()
        history = []
        for row in rows:
            before, after = _observation(row['state_before_json']), _observation(row['state_after_json'])
            if before is not None and after is not None:
                history.append((row['action'], before, after))
        state = state_before if isinstance(state_before, dict) else {}
        signals = {}
        for target in NUMERIC_TARGETS:
            current = _numeric(state.get(target), target)
            if current is None:
                signals[target] = _unavailable(state, target)
                continue
            samples = []
            for selected, before, after in history:
                old, new = _numeric(before.get(target), target), _numeric(after.get(target), target)
                if old is not None and new is not None:
                    samples.append((selected, new - old))
            evidence, level = _select_evidence(samples, action)
            # Normalize to [-1,1] before summing: even summing x/n can overflow
            # after rounding when several valid deltas approach float's limit.
            scale = max((abs(value) for value in evidence), default=0)
            delta = scale * (math.fsum(value / scale for value in evidence) / len(evidence)) if scale else 0
            raw = current + delta
            ceiling = 100.0 if target != 'load_ratio' else sys.float_info.max
            value = min(ceiling, max(0.0, raw))
            signals[target] = {'status': 'predicted', 'value': value,
                               'method': level + '_mean_delta' if evidence else 'persistence',
                               'clamped': value != raw, **_support(len(evidence))}

        # Existing observations call this field "network"; keep that schema intact.
        current = state.get('network')
        if type(current) is not bool:
            signals['network_reachable'] = _unavailable(state, 'network')
        else:
            samples = [(selected, after['network']) for selected, _, after in history
                       if type(after.get('network')) is bool]
            evidence, level = _select_evidence(samples, action)
            signal = {'status': 'predicted', 'method': 'persistence',
                      'value': current, **_support(len(evidence))}
            if evidence:
                probability = sum(evidence) / len(evidence)
                signal.update(method=level + '_boolean_frequency', value=probability >= .5,
                              probability_true=probability)
            signals['network_reachable'] = signal
        return Prediction(action=action, signals=signals)
