"""Parent-only stationary-action-v2 truth. No policy or exposure intervention."""
import json
import math
from types import MappingProxyType

from ..contracts import ContractError, validate_event_key
from ..registry import ACTIONS
from .private import PrivateTruthView, ScenarioEngine

COMMON = MappingProxyType(dict(battery_pct=80, charging=False, load_ratio=.5,
                              disk_free_pct=50, network=False, local_hour=12))
EFFECTS = MappingProxyType(dict(observe=0., rest=-.10, reflect=.10, consolidate=.05))


def validate_action_effects(effects):
    if (type(effects) is not dict or set(effects) != set(ACTIONS)
            or any(type(x) not in (int, float) or not math.isfinite(x) for x in effects.values())
            or len(set(effects.values())) < 2):
        raise ContractError()


class StationaryScenario(ScenarioEngine):
    identity = 'stationary-action-v2'

    def __init__(self, protocol='PREQUENTIAL'):
        if protocol not in ('PREQUENTIAL', 'FROZEN_SELECTION_ASSAY'):
            raise ContractError()
        validate_action_effects(dict(EFFECTS))
        self.protocol = protocol
        self._private = PrivateTruthView(json.dumps({'scenario': self.identity,
            'effects': dict(EFFECTS), 'reset': dict(COMMON)}, sort_keys=True).encode())

    def _ordinal(self, key):
        phase, subcase, ordinal, stage = validate_event_key(list(key))
        limits = {'measured': 400} if self.protocol == 'PREQUENTIAL' else {'training': 320, 'probe': 80}
        if subcase != 'default' or phase not in limits or ordinal > limits[phase]:
            raise ContractError()
        return ordinal

    def initial_observation(self, key):
        self._ordinal(key)
        return dict(COMMON)

    def reset_event(self, key):
        self._ordinal(key)
        return {'kind': 'exogenous_reset', 'key': list(key), 'observation': dict(COMMON)}

    def _load_delta(self, action, ordinal):
        return EFFECTS[action]

    def apply_action(self, action, key):
        ordinal = self._ordinal(key)
        if action not in ACTIONS:
            raise ContractError()
        return dict(COMMON, battery_pct=79.75, disk_free_pct=49.95, network=True,
                    load_ratio=.5 + self._load_delta(action, ordinal))
