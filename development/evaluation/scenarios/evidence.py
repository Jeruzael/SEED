"""Parent-only evidence-v1 frozen observations, never mutable probe setup."""
import json
from ..contracts import ContractError, validate_event_key
from ..registry import ACTIONS
from .private import PrivateTruthView, ScenarioEngine
from .stationary import COMMON


class EvidenceScenario(ScenarioEngine):
    identity = 'evidence-v1'
    def __init__(self, variant):
        subcases = dict(cold='fresh', conflict='contradictory', unavailable='unavailable', stale='stale')
        if variant not in subcases:
            raise ContractError()
        self.variant, self.subcase = variant, subcases[variant]
        self._private = PrivateTruthView(json.dumps({'scenario': self.identity, 'variant': variant}).encode())

    def initial_observation(self, key):
        phase, subcase, ordinal, stage = validate_event_key(list(key))
        if phase != 'probe' or subcase != self.subcase or ordinal > 16:
            raise ContractError()
        observation = dict(COMMON)
        if self.variant == 'unavailable':
            observation.pop('load_ratio'); observation.pop('disk_free_pct')
            observation.update(battery_pct=None, network=None)
        return observation

    def apply_action(self, action, key):
        if action not in ACTIONS:
            raise ContractError()
        # An assay only observes frozen projections: no claimed internal effects.
        return self.initial_observation(key)
