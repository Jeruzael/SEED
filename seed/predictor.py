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


@dataclass(frozen=True)
class PredictionBatch:
    predictions: dict
    contributors: dict


def _clock_summary(rows):
    valid = []
    invalid = 0
    for row in rows:
        clock = row.get('completed_at')
        if type(clock) in (int, float) and math.isfinite(clock) and clock >= 0:
            valid.append((clock, row.get('id', 0)))
        else:
            invalid += 1
    newest = max(valid) if valid else (None, None)
    return dict(newest_source_transition_id=newest[1],
                newest_source_completed_at=newest[0], invalid_source_count=invalid)


class Predictor:
    def __init__(self, memory):
        self.memory = memory

    def predict(self, state_before: dict, action: str) -> Prediction:
        # Every persisted B1 transition is completed. Limit raw rows first, so
        # malformed history cannot cause an unbounded search for valid samples.
        with self.memory._lock:
            rows = self.memory.db.execute('''SELECT action,state_before_json,state_after_json
                FROM transitions ORDER BY id DESC LIMIT ?''', (HISTORY_LIMIT,)).fetchall()
        return Prediction(**self.predict_candidates(state_before, (action,), snapshot=rows).predictions[action])

    def predict_candidates(self, state_before, actions, *, snapshot):
        """Pure batch inference over one caller-owned snapshot; decode each row once."""
        history = []
        for source in snapshot:
            row = dict(source)
            before, after = _observation(row['state_before_json']), _observation(row['state_after_json'])
            if before is not None and after is not None:
                history.append((row, before, after))
        predictions, contributors = {}, {}
        for action in actions:
            prediction, sources = self._predict_parsed(state_before, action, history)
            predictions[action], contributors[action] = prediction.to_dict(), sources
        return PredictionBatch(predictions, contributors)

    @staticmethod
    def _predict_parsed(state_before, action, history):
        state = state_before if isinstance(state_before, dict) else {}
        signals, sources = {}, {}
        for target in NUMERIC_TARGETS:
            sources[target] = _clock_summary([])
            current = _numeric(state.get(target), target)
            if current is None:
                signals[target] = _unavailable(state, target)
                continue
            samples = []
            for row, before, after in history:
                old, new = _numeric(before.get(target), target), _numeric(after.get(target), target)
                if old is not None and new is not None:
                    samples.append((row, new - old))
            matched = [(row, delta) for row, delta in samples if row['action'] == action]
            selected, level = (matched, 'action') if len(matched) >= MIN_SAMPLES else (samples, 'global')
            if len(selected) < MIN_SAMPLES:
                selected, level = [], 'persistence'
            evidence = [delta for _, delta in selected]
            sources[target] = _clock_summary([row for row, _ in selected])
            # Preserve B2's scaled mean and clamp, including extreme finite values.
            scale = max((abs(value) for value in evidence), default=0)
            delta = scale * (math.fsum(value / scale for value in evidence) / len(evidence)) if scale else 0
            raw = current + delta
            ceiling = 100.0 if target != 'load_ratio' else sys.float_info.max
            value = min(ceiling, max(0.0, raw))
            signals[target] = {'status': 'predicted', 'value': value,
                               'method': level + '_mean_delta' if evidence else 'persistence',
                               'clamped': value != raw, **_support(len(evidence))}
        current = state.get('network')
        if type(current) is not bool:
            signals['network_reachable'] = _unavailable(state, 'network')
        else:
            samples = [(row['action'], after['network']) for row, _, after in history
                       if type(after.get('network')) is bool]
            evidence, level = _select_evidence(samples, action)
            signal = {'status': 'predicted', 'method': 'persistence',
                      'value': current, **_support(len(evidence))}
            if evidence:
                probability = sum(evidence) / len(evidence)
                signal.update(method=level + '_boolean_frequency', value=probability >= .5,
                              probability_true=probability)
            signals['network_reachable'] = signal
        return Prediction(action=action, signals=signals), sources
