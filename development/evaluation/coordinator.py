"""Parent-only admission scaffold. Scientific dispatch remains unauthorized."""
import time
import hashlib
from dataclasses import dataclass
from .analysis import expand_inventory, require_frozen
from .contracts import (ContractError, FrozenPlan, RunRequest,
                        VerificationReport, strict_json)
from .dependency import audit_dependencies
from .limits import Budget
from .specs import CAPS


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


# --------------------------------------------------------------- I30 tooling
# Bounded suite inventory and reconciliation. Both operations are pure:
# they never launch workers, create learner state, execute a scenario or
# write artifacts, and neither weakens the dispatch lock above.

_TERMINAL_STATUSES = ('COMPLETED', 'FAILED', 'INCOMPLETE', 'INVALID')


@dataclass(frozen=True)
class MemberEvidence:
    """Recorded evidence for one registered suite member.

    The implementation plan names a ``RunArtifact`` input for suite
    reconciliation; the contracts define no such type. This is the
    smallest compatible representation, projected from the immutable
    published evidence (run manifest status and identities, freeze
    receipt linkage, stored measurement inventory) without inventing
    a new published artifact schema. ``measurements`` carries the
    member's produced registered-measurement identities when the
    supplied evidence includes an inventory, else ``None``.
    """

    identity: str
    status: str
    plan_digest: str
    seed: int
    protocol: str
    variant: str
    run_id: str | None = None
    receipt_digest: str | None = None
    measurements: tuple[str, ...] | None = None


def _plan_body(plan):
    if type(plan) is not FrozenPlan:
        raise ContractError()
    return strict_json(plan.plan.body, max_bytes=CAPS['plan_bytes'])


def registered_suite(plan: FrozenPlan) -> tuple[RunRequest, ...]:
    """The frozen plan's registered members as bounded run requests.

    Pure planning: one request per registered member, in frozen
    member order, with the plan's own identities -- nothing is
    inferred, substituted or dropped. Inventories beyond the
    approved ceilings (CAPS seeds / runs, counting every member
    including policy counterparts and future re-executions) are
    rejected before any work begins.
    """
    body = _plan_body(plan)
    members = body['members']
    if len(body['seeds']) > CAPS['seeds'] or len(members) > CAPS['runs']:
        raise ContractError()
    identities = [member['id'] for member in members]
    if len(set(identities)) != len(identities):
        raise ContractError()
    return tuple(RunRequest(identity=identity) for identity in identities)


def verify_suite(plan: FrozenPlan,
                 members: tuple[MemberEvidence, ...]) -> VerificationReport:
    """Reconcile supplied member evidence against the registered suite.

    Every planned member stays in the denominator: missing,
    duplicated, unexpected, mismatched, non-terminal, incomplete and
    evidence-free members are each reported by identity. A member
    reconciles only when its recorded identity, seed, protocol and
    variant match the frozen definition, its evidence is bound to
    this plan's digest, it reached a terminal COMPLETED status, and
    it carries published run and receipt identities. A supplied
    measurement inventory must match the member's registered
    inventory exactly. The report verifies reconciliation of
    recorded evidence; it is not itself scientific proof and never
    fabricates a finding.
    """
    body = _plan_body(plan)
    if type(members) is not tuple or \
            any(type(member) is not MemberEvidence for member in members):
        raise ContractError()
    expected = {member['id']: member for member in body['members']}
    reasons = []
    seen = {}
    for evidence in members:
        if evidence.identity in seen:
            reasons.append(f'duplicate member: {evidence.identity}')
        seen.setdefault(evidence.identity, evidence)
        if evidence.identity not in expected:
            reasons.append(f'unexpected member: {evidence.identity}')
        if evidence.plan_digest != plan.digest:
            reasons.append(f'plan digest mismatch: {evidence.identity}')
    inventory = None
    for identity, definition in expected.items():
        evidence = seen.get(identity)
        if evidence is None:
            reasons.append(f'missing member: {identity}')
            continue
        if evidence.seed != definition['seed']:
            reasons.append(f'seed mismatch: {identity}')
        if evidence.protocol != definition['protocol']:
            reasons.append(f'protocol mismatch: {identity}')
        if evidence.variant != definition['variant']:
            reasons.append(f'variant mismatch: {identity}')
        if evidence.status not in _TERMINAL_STATUSES:
            reasons.append(f'invalid terminal status: {identity}')
        elif evidence.status != 'COMPLETED':
            reasons.append(
                f'member did not complete: {identity}: {evidence.status}')
        elif not evidence.run_id or not evidence.receipt_digest:
            reasons.append(f'missing published evidence: {identity}')
        if evidence.measurements is not None:
            if len(set(evidence.measurements)) != len(evidence.measurements):
                reasons.append(f'duplicate measurement identity: {identity}')
            if evidence.status == 'COMPLETED':
                if inventory is None:
                    inventory = {}
                    for row in expand_inventory(plan.plan):
                        inventory.setdefault(row.member, set()).add(row.identity)
                registered = inventory.get(identity, set())
                supplied = set(evidence.measurements)
                if registered - supplied:
                    reasons.append(
                        f'measurement inventory omission: {identity}')
                if supplied - registered:
                    reasons.append(f'unregistered measurement: {identity}')
    return VerificationReport(gate='suite', passed=not reasons,
                              reasons=tuple(sorted(reasons)))


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
