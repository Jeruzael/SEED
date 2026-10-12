"""I30: bounded registered-suite inventory and reconciliation tooling.

These tests qualify engineering interfaces only. Building the
inventory never dispatches a member, and reconciling synthetic
member evidence never claims an empirical result: the evidence
tuples below are technical fixtures with explicit provenance.
"""
import copy
from dataclasses import replace

import pytest

from development.evaluation.analysis import (
    analysis_digest, default_plan, expand_inventory, freeze_plan)
from development.evaluation.canonical import canonical_bytes
from development.evaluation.contracts import (
    AnalysisPlan, ContractError, FrozenPlan, RunRequest)
from development.evaluation.coordinator import (
    Coordinator, MemberEvidence, registered_suite, verify_suite)
from development.evaluation.limits import Budget
from development.evaluation.specs import CAPS

from .test_analysis import ClosedRoot

FAMILY_COUNTS = {'A': 10, 'B': 5, 'C': 5, 'D': 10}


def frozen_default(tmp_path):
    return freeze_plan(default_plan(), ClosedRoot(tmp_path))


def plan_body(plan):
    from development.evaluation.contracts import strict_json
    return strict_json(plan.plan.body, max_bytes=CAPS['plan_bytes'])


def synthetic_frozen(body):
    """A FrozenPlan built directly from a body, bypassing validate_plan.

    Admission arithmetic (seed/run ceilings) belongs to the suite
    tooling itself, so boundary tests must be able to present
    inventories the plan validator would also reject upstream.
    """
    frozen_body = canonical_bytes(body)
    plan = AnalysisPlan(body=frozen_body)
    return FrozenPlan(plan=plan, digest=analysis_digest(plan), receipt=b'')


def eight_seed_body():
    body = plan_body_from_default()
    members = []
    template = body['members']
    for seed in range(8):
        for member in template:
            if member['seed'] != 0:
                continue
            clone = copy.deepcopy(member)
            clone['id'] = member['id'].rsplit('-', 1)[0] + '-' + str(seed)
            clone['seed'] = seed
            members.append(clone)
    body['members'] = members
    body['seeds'] = list(range(8))
    return body


def plan_body_from_default():
    from development.evaluation.contracts import strict_json
    return strict_json(default_plan().body, max_bytes=CAPS['plan_bytes'])


# ---------------------------------------------------------------- Phase A --

def test_suite_expansion_and_accounting(tmp_path):
    plan = frozen_default(tmp_path)
    suite = registered_suite(plan)
    body = plan_body(plan)

    # Exactly the registered members, in frozen order, nothing invented.
    assert len(suite) == 30
    assert [r.identity for r in suite] == [m['id'] for m in body['members']]
    assert len({r.identity for r in suite}) == 30
    assert all(type(r) is RunRequest and r.count == 1 for r in suite)
    assert all(r.reservation_bytes == CAPS['reservation_bytes'] for r in suite)

    # Family distribution A10 / B5 / C5 / D10; C stays one bundle per seed
    # and D's random-eligible trajectory is its own counted member.
    counts = {}
    for member in body['members']:
        counts[member['family']] = counts.get(member['family'], 0) + 1
    assert counts == FAMILY_COUNTS
    identities = [r.identity for r in suite]
    assert sum(1 for i in identities if i.startswith('c-')) == 5
    assert sum(1 for i in identities if i.startswith('d-random-eligible-')) == 5
    assert {m['seed'] for m in body['members']} == {0, 1, 2, 3, 4}

    # Deterministic: repeated calls are identical, byte for byte.
    again = registered_suite(plan)
    assert again == suite
    assert canonical_bytes([r.identity for r in suite]) == \
        canonical_bytes([r.identity for r in again])

    # Eight seeds expand the default families to 48 requests: rejected
    # before any work begins (the 32-run suite ceiling binds).
    with pytest.raises(ContractError):
        registered_suite(synthetic_frozen(eight_seed_body()))

    # The seed ceiling binds independently of the run ceiling.
    nine = plan_body_from_default()
    nine['seeds'] = list(range(9))
    with pytest.raises(ContractError):
        registered_suite(synthetic_frozen(nine))

    # Exactly 32 registered runs are admitted; 33 are rejected. No member
    # is silently dropped to satisfy the limit.
    base = plan_body_from_default()
    members = []
    for index in range(33):
        clone = copy.deepcopy(base['members'][0])
        clone['id'] = 'member-' + str(index)
        members.append(clone)
    at_cap = copy.deepcopy(base); at_cap['members'] = members[:32]
    assert len(registered_suite(synthetic_frozen(at_cap))) == 32
    over_cap = copy.deepcopy(base); over_cap['members'] = members
    with pytest.raises(ContractError):
        registered_suite(synthetic_frozen(over_cap))


def test_registered_suite_rejects_non_frozen_input():
    with pytest.raises(ContractError):
        registered_suite(default_plan())
    with pytest.raises(ContractError):
        registered_suite(None)


# ---------------------------------------------------------------- Phase B --

def evidence_for(plan):
    body = plan_body(plan)
    rows = []
    for index, member in enumerate(body['members']):
        rows.append(MemberEvidence(
            identity=member['id'], status='COMPLETED',
            plan_digest=plan.digest, seed=member['seed'],
            protocol=member['protocol'], variant=member['variant'],
            run_id=format(index + 1, '032x'),
            receipt_digest=format(index + 1, '064x')))
    return tuple(rows)


def test_verify_suite_accepts_exact_reconciliation(tmp_path):
    plan = frozen_default(tmp_path)
    report = verify_suite(plan, evidence_for(plan))
    assert report.passed and report.status == 'PASS' and report.reasons == ()
    assert report.gate == 'suite'


def test_verify_suite_member_accounting_failures(tmp_path):
    plan = frozen_default(tmp_path)
    good = evidence_for(plan)
    member = good[0].identity

    def fails(rows, fragment):
        report = verify_suite(plan, rows)
        assert not report.passed and report.status == 'FAILED'
        assert any(fragment in reason for reason in report.reasons), report.reasons

    fails(good[1:], 'missing member: ' + member)
    fails(good + (good[0],), 'duplicate member: ' + member)
    extra = replace(good[0], identity='z-invented-0', run_id='f' * 32)
    fails(good + (extra,), 'unexpected member: z-invented-0')
    fails(good[:29], 'missing member')
    fails((replace(good[0], seed=99),) + good[1:], 'seed mismatch: ' + member)
    fails((replace(good[0], variant='invented'),) + good[1:],
          'variant mismatch: ' + member)
    fails((replace(good[0], protocol='INVENTED'),) + good[1:],
          'protocol mismatch: ' + member)
    fails((replace(good[0], plan_digest='0' * 64),) + good[1:],
          'plan digest mismatch: ' + member)
    fails((replace(good[0], status='RUNNING'),) + good[1:],
          'invalid terminal status: ' + member)
    fails((replace(good[0], status='FAILED'),) + good[1:],
          'did not complete: ' + member)
    fails((replace(good[0], status='INCOMPLETE'),) + good[1:],
          'did not complete: ' + member)
    fails((replace(good[0], run_id=None),) + good[1:],
          'missing published evidence: ' + member)
    fails((replace(good[0], receipt_digest=None),) + good[1:],
          'missing published evidence: ' + member)
    # A failed member relabeled COMPLETED without published evidence is a
    # misrepresentation, not a completion.
    fails((replace(good[0], status='COMPLETED', run_id=None,
                   receipt_digest=None),) + good[1:],
          'missing published evidence: ' + member)


def test_verify_suite_measurement_inventory(tmp_path):
    plan = frozen_default(tmp_path)
    body = plan_body(plan)
    member_id = body['members'][0]['id']
    registered = tuple(row.identity for row in expand_inventory(plan.plan)
                       if row.member == member_id)
    assert registered  # the registered inventory is nonempty by construction

    def with_measurements(measurements):
        return tuple(replace(row, measurements=measurements)
                     if row.identity == member_id else row
                     for row in evidence_for(plan))

    assert verify_suite(plan, with_measurements(registered)).passed
    report = verify_suite(plan, with_measurements(registered[1:]))
    assert not report.passed
    assert any('measurement inventory omission' in r and member_id in r
               for r in report.reasons)
    report = verify_suite(plan, with_measurements(registered + registered[:1]))
    assert not report.passed
    assert any('duplicate measurement' in r for r in report.reasons)
    report = verify_suite(plan, with_measurements(
        registered + ('invented:measurement',)))
    assert not report.passed
    assert any('unregistered measurement' in r for r in report.reasons)


# ------------------------------------------------------------- Phases C/F --

def test_reservation_bounds_and_exhaustion_typing():
    budget = Budget(retained_bytes=0, retained_runs=0)
    budget.reserve(RunRequest('at-cap', count=32))
    with pytest.raises(ContractError):  # one run over the 32-run ceiling
        Budget(retained_bytes=0, retained_runs=0).reserve(
            RunRequest('over-cap', count=33))
    with pytest.raises(ContractError):  # reservation size ceiling is exact
        Budget(retained_bytes=0, retained_runs=0).reserve(
            RunRequest('too-big', reservation_bytes=CAPS['reservation_bytes'] + 1))
    # Exhaustion is a typed contract failure, never a scientific outcome.
    full = Budget(retained_bytes=CAPS['root_bytes'], retained_runs=0)
    with pytest.raises(ContractError):
        full.reserve(RunRequest('no-room'))


def test_admission_accounting_and_no_partial_suite(tmp_path):
    from development.evaluation.paths import EvaluationRoot
    root = EvaluationRoot.create(tmp_path.resolve())
    plan = freeze_plan(default_plan(), root)
    coordinator = Coordinator(root=root, frozen_plan=plan)
    suite = registered_suite(plan)
    for request in suite:  # all 30 registered members admitted
        assert coordinator.admit(request) is request
    with pytest.raises(ContractError):  # the same member twice is not a run
        coordinator.admit(suite[0])
    fresh = Coordinator(root=None, frozen_plan=plan)
    with pytest.raises(ContractError):  # no root/plan, no admission, no work
        fresh.admit(suite[0])


def test_dispatch_lock_survives_i30_tooling(tmp_path, capsys):
    from development.evaluation import cli
    plan = frozen_default(tmp_path)
    coordinator = Coordinator(root=None, frozen_plan=plan)
    with pytest.raises(RuntimeError, match='FOUNDATION_ONLY_DISPATCH_DISABLED'):
        coordinator.dispatch(registered_suite(plan)[0])
    for verb in ('run', 'suite', 'reexecute'):
        assert cli.main([verb, 'a' * 32]) == 2
        assert 'EMPIRICAL_DISPATCH_DISABLED' in capsys.readouterr().out
    # Unregistered selectors and arbitrary input never reach dispatch.
    assert cli.main(['suite', 'b10-shared-suite']) == 3
    assert cli.main(['invented', 'a' * 32]) == 3
    assert cli.main(['run', 'https://example.invalid/x']) == 3
    assert cli.main(['run', '/tmp/anything']) == 3
    capsys.readouterr()
