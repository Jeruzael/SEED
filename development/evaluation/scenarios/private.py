"""Parent-only truth capability and detached observation boundary primitives."""
from dataclasses import dataclass
from ..contracts import ContractError, validate_observation


@dataclass(frozen=True)
class PrivateTruthView:
    body: bytes

    def __post_init__(self):
        if type(self.body) is not bytes or len(self.body)>64*1024:
            raise ContractError()


class ScenarioEngine:
    """Fixed admitted public data transport, not an A–D scientific engine."""
    def __init__(self, initial, outcomes, private_view):
        if type(private_view) is not PrivateTruthView or type(outcomes) is not list or not 1<=len(outcomes)<=1024:
            raise ContractError()
        self._initial=validate_observation(initial)
        self._outcomes=tuple(validate_observation(x) for x in outcomes)
        self._private=private_view

    def initial_observation(self, key):
        if key[2]>len(self._outcomes):
            raise ContractError()
        return dict(self._initial)

    def apply_action(self, action, key):
        if not 1<=key[2]<=len(self._outcomes):
            raise ContractError()
        return dict(self._outcomes[key[2]-1])

    def evaluator_view(self):
        return self._private
