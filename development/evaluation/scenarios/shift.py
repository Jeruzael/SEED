"""Parent-only rest-shift-v2; boundary never enters learner observations."""
import json
from ..contracts import ContractError, validate_event_key
from .private import PrivateTruthView
from .stationary import EFFECTS, StationaryScenario


class ShiftScenario(StationaryScenario):
    identity = 'rest-shift-v2'

    def __init__(self):
        super().__init__()
        self._private = PrivateTruthView(json.dumps({'scenario': self.identity,
            'boundary': 321, 'changed_action': 'rest', 'new_delta': .05,
            'old_effects': dict(EFFECTS)}, sort_keys=True).encode())

    def _ordinal(self, key):
        phase, subcase, ordinal, stage = validate_event_key(list(key))
        if phase != 'measured' or subcase != 'default' or ordinal > 800:
            raise ContractError()
        return ordinal

    def _load_delta(self, action, ordinal):
        return .05 if action == 'rest' and ordinal >= 321 else EFFECTS[action]
