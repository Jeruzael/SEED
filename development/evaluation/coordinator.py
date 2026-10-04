"""Parent-only admission scaffold. Scientific dispatch remains unauthorized."""
import time
import hashlib
from .analysis import require_frozen
from .contracts import ContractError, RunRequest
from .dependency import audit_dependencies
from .limits import Budget


class Coordinator:
    def __init__(self, *, root=None, frozen_plan=None, suite_seconds=1800, clock=time.monotonic):
        if type(suite_seconds) not in (int,float) or not 0<suite_seconds<=1800:
            raise ContractError()
        self.root,self.frozen_plan,self.suite_seconds=root,frozen_plan,suite_seconds
        self._clock,self._started=clock,clock()
        self._budget=None

    def admit(self, request: RunRequest):
        if self.root is None or self.frozen_plan is None or self._clock()-self._started>=self.suite_seconds:
            raise ContractError()
        if audit_dependencies(self.root.path.parent):
            raise ContractError()
        require_frozen(self.frozen_plan.plan,self.root)
        usage=self.root.usage()
        if self._budget is None:
            self._budget=self.root.budget
        self._budget.reconcile(usage)
        self._budget.reserve(request)
        return request

    def dispatch(self, *args, **kwargs):
        # G3–G7 and I09+ are intentionally locked, even with a frozen plan.
        raise RuntimeError('FOUNDATION_ONLY_DISPATCH_DISABLED')


def prepare_policy_pair(owned, slot, *, seed, identity, close_owner=None):
    """Worker-owned equal-start clone preparation; no scientific dispatch."""
    from .state import OwnedState, _worker_only
    from .baselines import configure_policy
    from .canonical import canonical_bytes
    from .determinism import _seed
    from .specs import digest, integer
    from .contracts import WorkerLaunch
    _worker_only()
    digest(identity); integer(seed, 0, 2**63-1)
    if type(owned) is not OwnedState or owned._closed:
        raise ContractError()
    before = owned.raw_tables()
    clone = owned.clone(slot)
    try:
        if clone.raw_tables() != before:
            raise ContractError()
        result = dict(initial_digest=hashlib.sha256(canonical_bytes(before)).hexdigest(),
                      prediction_pairing='not_paired_divergent_policy_trajectories')
        for role, state in (('seed', owned), ('random-eligible', clone)):
            settings = configure_policy(state, role)
            fixture = state.complete_fixture(close_owner=close_owner if role == 'seed' else None)
            role_identity = [identity, 'constrained-v1', seed, role]
            rng_seed = _seed('SEED_B10_POLICY_ROLE_V1', role_identity)
            uuid_identity = format(_seed('SEED_B10_POLICY_UUID_V1', role_identity), '064x')
            result[role] = WorkerLaunch(fixture.learner, settings, rng_seed, uuid_identity,
                launch_mode='COMPLETED_OWNED_FIXTURE', fixture=fixture)
        return result
    except BaseException:
        clone.close()
        raise
