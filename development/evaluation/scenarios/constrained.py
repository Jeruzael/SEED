"""Parent-only constrained-v1 contexts and external evaluator utility."""
import json
from ..contracts import ContractError, validate_event_key
from ..registry import ACTIONS
from .private import PrivateTruthView, ScenarioEngine
from .stationary import COMMON, EFFECTS


class ConstrainedScenario(ScenarioEngine):
    identity = 'constrained-v1'
    def __init__(self):
        contexts = [dict(COMMON) for _ in range(8)]
        contexts[1]['load_ratio'] = .9
        contexts[2]['battery_pct'] = 15
        contexts[3]['disk_free_pct'] = 5
        contexts[4]['battery_pct'] = None
        contexts[5]['charging'] = None
        contexts[6].pop('load_ratio')
        contexts[7].pop('disk_free_pct')
        self._contexts = tuple(contexts)
        self._private = PrivateTruthView(json.dumps({'scenario': self.identity,
            'contexts': contexts, 'effects': dict(EFFECTS)}, sort_keys=True).encode())

    def initial_observation(self, key):
        phase, subcase, ordinal, stage = validate_event_key(list(key))
        if phase != 'measured' or subcase != 'default' or ordinal > 128:
            raise ContractError()
        return dict(self._contexts[(ordinal-1) % 8])

    def reset_event(self, key):
        return {'kind': 'exogenous_reset', 'key': list(key), 'observation': self.initial_observation(key)}

    def apply_action(self, action, key):
        if action not in ACTIONS:
            raise ContractError()
        outcome = self.initial_observation(key)
        if 'load_ratio' in outcome:
            outcome['load_ratio'] = max(0., outcome['load_ratio'] + EFFECTS[action])
        outcome['network'] = action in ('observe', 'reflect')
        return outcome


def task_utility(observation, action):
    if action not in ACTIONS:
        raise ContractError()
    from seed.decision import constraints
    constrained = bool(constraints(observation, 'reflect'))
    return (dict(rest=1., observe=.25, reflect=0., consolidate=0.) if constrained
            else dict(reflect=1., consolidate=.75, observe=.5, rest=.25))[action]
