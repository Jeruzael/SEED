"""Observed differences only: no causal attribution, predictions, or policy changes."""
import json
import math


def validated_state(state: dict) -> dict:
    """Detach a finite JSON observation without filling in missing sensors."""
    if not isinstance(state, dict) or any(not isinstance(key, str) for key in state):
        raise ValueError('An observation must be a dictionary with string keys')
    return json.loads(json.dumps(state, sort_keys=True, allow_nan=False))


def describe_outcome(before: dict, after: dict) -> dict:
    before, after = validated_state(before), validated_state(after)
    outcome = {}
    for key in sorted(before.keys() | after.keys()):
        old, new = before.get(key), after.get(key)
        item = {'before': old, 'after': new,
                'before_present': key in before, 'after_present': key in after}
        if type(old) in (int, float) and type(new) in (int, float):
            delta = new - old
            if isinstance(delta, float) and not math.isfinite(delta):
                item.update(delta=None, delta_unavailable=True)
            else:
                item['delta'] = delta
        else:
            item['changed'] = (type(old) is not type(new) or old != new or
                               (key in before) != (key in after))
        outcome[key] = item
    return outcome
