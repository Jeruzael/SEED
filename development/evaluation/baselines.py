"""Evaluator baselines; policy settings are admitted only before measurement."""
import json
import hashlib
import math
import sys
from .contracts import ContractError
from .registry import ACTIONS


def _number(value, target):
    if type(value) not in (int, float):
        return None
    try:
        value = float(value)
    except OverflowError:
        return None
    if not math.isfinite(value) or value < 0 or (target != 'load_ratio' and value > 100):
        return None
    return value


def _state(raw):
    if type(raw) is not str or len(raw) > 16384:
        return None
    try:
        value = json.loads(raw)
    except (ValueError, TypeError, RecursionError):
        return None
    return value if type(value) is dict else None


def forecast_baselines(observation, action, history, cutoff):
    """Two forecasts over the same prior raw pool, never the current target.

    A null cutoff denotes the captured empty history, even if the supplied
    database snapshot has since grown. Corrupt rows consume raw positions.
    """
    from .contracts import validate_observation
    observation = validate_observation(observation)
    if (action not in ACTIONS or type(history) is not tuple or len(history) > 1024
            or (cutoff is not None and (type(cutoff) is not int or not 0 <= cutoff < 2**63))):
        raise ContractError()
    ids = set()
    admitted = []
    for source in history:
        if type(source) is not dict or type(source.get('id')) is not int or not 1 <= source['id'] < 2**63 or source['id'] in ids:
            raise ContractError()
        ids.add(source['id'])
        if cutoff is not None and source['id'] <= cutoff:
            admitted.append(source)
    raw = sorted(admitted, key=lambda r: r['id'], reverse=True)[:200]
    projection = [{k: r.get(k) for k in ('id', 'action', 'state_before_json', 'state_after_json', 'completed_at')} for r in raw]
    try:
        serialized = json.dumps(projection, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise ContractError() from None
    if len(serialized) > 200*33000:
        raise ContractError()
    parsed = []
    oversized = any(type(r.get(k)) is str and len(r[k]) > 16384 for r in raw for k in ('state_before_json', 'state_after_json'))
    if not oversized:
        for row in raw:
            before, after = _state(row.get('state_before_json')), _state(row.get('state_after_json'))
            if before is not None and after is not None:
                parsed.append((row['id'], before, after))
    result = dict(history=dict(cutoff_transition_id=cutoff, raw_rows_examined=len(raw),
        raw_ids=[r['id'] for r in raw], source_digest=hashlib.sha256(b'SEED_B10_BASELINE_RAW_V1\0'+serialized).hexdigest(),
        reason='oversized_history' if oversized else None), action=action)
    for baseline in ('persistence', 'global-history'):
        signals = {}
        for target in ('battery_pct', 'load_ratio', 'disk_free_pct', 'network_reachable'):
            network = target == 'network_reachable'
            key = 'network' if network else target
            current = observation.get(key) if network else _number(observation.get(key), target)
            if current is None or (network and type(current) is not bool):
                signals[target] = dict(status='unavailable', value=None, evidence_count=0, source_ids=[],
                    reason='missing_current_value' if key not in observation else 'invalid_current_value')
                continue
            samples = []
            if baseline == 'global-history':
                for identity, before, after in parsed:
                    if network:
                        if type(after.get('network')) is bool:
                            samples.append((identity, after['network']))
                    else:
                        old, new = _number(before.get(target), target), _number(after.get(target), target)
                        if old is not None and new is not None:
                            samples.append((identity, new-old))
            candidate_ids = [n for n, _ in samples]
            if len(samples) < 2:
                samples = []
            signal = dict(status='predicted', value=current, method='persistence',
                evidence_count=len(samples), source_ids=[n for n, _ in samples], clamped=False,
                candidate_source_ids=candidate_ids, candidate_usable_count=len(candidate_ids),
                reason='INSUFFICIENT_SUPPORT' if baseline == 'global-history' and not samples else None)
            if samples and network:
                probability = math.fsum(int(value) for _, value in samples) / len(samples)
                signal.update(method='global_boolean_frequency', value=probability >= .5, probability_true=probability)
            elif samples:
                scale = max(abs(value) for _, value in samples)
                delta = scale * (math.fsum(value/scale for _, value in samples) / len(samples)) if scale else 0.
                predicted = current + delta
                value = min(sys.float_info.max if target == 'load_ratio' else 100., max(0., predicted))
                signal.update(method='global_mean_delta', value=value, clamped=value != predicted)
            signals[target] = signal
        result[baseline] = dict(signals=signals)
    return result


def configure_policy(owned, role):
    from .state import OwnedState, _worker_only
    _worker_only()
    if type(owned) is not OwnedState or owned._closed or role not in ('seed', 'random-eligible'):
        raise ContractError()
    db = owned.memory.db
    if db.in_transaction or db.execute('SELECT COUNT(*) FROM transitions').fetchone()[0]:
        raise ContractError()
    settings = json.loads(db.execute('SELECT data_json FROM settings WHERE singleton=1').fetchone()[0])
    settings.update(epsilon=.15 if role == 'seed' else 1., alpha=.18)
    from seed.config import validate_settings
    settings = validate_settings(settings)
    raw = json.dumps(settings, sort_keys=True, separators=(',', ':')).encode()
    with db:
        db.execute('UPDATE settings SET data_json=? WHERE singleton=1', (raw.decode(),))
    return raw
