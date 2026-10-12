"""I30 standalone technical evaluation scenario.

Exercises the registered family/protocol engineering interfaces in
disposable evaluator-owned roots with synthetic, explicitly labeled
technical fixtures: family A stationary prediction under both the
prequential and frozen-assay protocols, family B rest-only regime
shift, family C frozen robustness subcases with evaluator-private
configuration, family D constrained decisions with a separately
prepared random-eligible policy trajectory, plus artifact
publication, recorded replay and honest failure evidence.

The output is a bounded machine-readable report whose classification
is TECHNICAL_FIXTURE. It is not an empirical scientific verdict, it
never touches an installed SEED home, and it does not run the
registered 30-member empirical suite.

Run: python -m tests.evaluation_scenario
"""
import importlib
import json
import multiprocessing
import sys
import tempfile
import traceback
from pathlib import Path

CLASSIFICATION = 'TECHNICAL_FIXTURE'


def _load(name):
    return importlib.import_module('development.evaluation.' + name)


def _check(checks, name, condition, detail=''):
    checks.append(dict(name=name, passed=bool(condition), detail=detail))
    return bool(condition)


def _prequential(root, run_id, scenario, measured):
    """One bounded prequential technical run in a disposable root."""
    channel = _load('channel')
    checkpoint = _load('checkpoint')
    contracts = _load('contracts')
    prequential = _load('prequential')
    worker_mod = _load('worker')
    cap = root.assign_learner(run_id, 0)
    journal = checkpoint.ScoreJournal.create(root, run_id)
    worker = worker_mod.WorkerHandle.start(
        contracts.WorkerLaunch(cap, b'{"epsilon":0}', 3, 'a' * 64),
        channel=channel.ChannelRouter(scenario, journal=journal))
    driver = prequential.PrequentialDriver(measured=measured)
    try:
        result = driver.run(contracts.RunRequest(run_id), worker)
        journal_lines = len(journal.path.read_bytes().splitlines())
        stages = [json.loads(event.body)['updates'] for event in driver.events]
        return result, journal_lines, stages
    finally:
        worker.stop()
        journal.close()


def _frozen_a_child(pipe, cap):
    """Family A frozen selection assay over fixed stored history."""
    frozen = owned = None
    try:
        from development.evaluation.bootstrap import install_worker_adapters
        from development.evaluation.contracts import WorkerLaunch
        from development.evaluation.state import OwnedState
        from development.evaluation.frozen import freeze_state, FrozenWorker
        from development.evaluation.fixtures import build_fixture
        from development.evaluation.scenarios.stationary import (
            StationaryScenario)
        streams = install_worker_adapters(
            WorkerLaunch(cap, b'{"epsilon":0.15}', 3, 'c' * 64))
        owned = OwnedState.fresh(cap, {'epsilon': .15})
        build_fixture('conflict', owned)
        fixture = freeze_state(owned)
        frozen = FrozenWorker(fixture, streams)
        before = frozen.raw_state()
        assay = StationaryScenario('FROZEN_SELECTION_ASSAY')

        class AClient:
            def observation(self, phase, ordinal, subcase='default'):
                return assay.initial_observation(
                    ('probe', subcase, ordinal, 'pre'))

            def apply(self, action, ordinal):
                return assay.apply_action(
                    action, ('probe', 'default', ordinal, 'outcome'))

        for ordinal in (1, 2):
            record = frozen.probe(
                assay.initial_observation(('probe', 'default', ordinal, 'pre')),
                ('probe', 'default', ordinal, 'pre'), AClient())
            assert json.loads(record.body)['assay_kind'] == \
                'FROZEN_SELECTION_ASSAY'
        assert frozen.raw_state() == before  # frozen path mutates nothing
        frozen.assert_unchanged()
        pipe.send(('ok', dict(a_frozen_probes=2)))
    except BaseException:
        traceback.print_exc()
        pipe.send(('error',))
    finally:
        if frozen:
            frozen.close()
        if owned:
            owned.close()
        pipe.close()


def _c_child(pipe, cap, variant):
    """Family C robustness: one evaluator-private variant per worker."""
    frozen = owned = None
    try:
        from development.evaluation.bootstrap import install_worker_adapters
        from development.evaluation.contracts import WorkerLaunch
        from development.evaluation.state import OwnedState
        from development.evaluation.frozen import freeze_state, FrozenWorker
        from development.evaluation.fixtures import build_fixture
        from development.evaluation.scenarios.evidence import EvidenceScenario
        streams = install_worker_adapters(
            WorkerLaunch(cap, b'{"epsilon":0.15}', 3, 'c' * 64))
        owned = OwnedState.fresh(cap, {'epsilon': .15})
        if variant != 'cold':
            build_fixture('conflict', owned)
        if variant != 'conflict':
            build_fixture(variant, owned)
        provenance = owned.fixture_provenance
        fixture = freeze_state(owned)
        frozen = FrozenWorker(fixture, streams)
        before = frozen.raw_state()
        scenario = EvidenceScenario(variant)

        class CClient:
            def apply(self, action, ordinal):
                return scenario.apply_action(
                    action, ('probe', scenario.subcase, ordinal, 'outcome'))

        for ordinal in (1, 2, 3, 4):
            key = ('probe', scenario.subcase, ordinal, 'pre')
            record = frozen.probe(
                scenario.initial_observation(key), key, CClient(),
                read_time=provenance['read_time'])
            assert json.loads(record.body)['assay_kind'] == \
                'FROZEN_SELECTION_ASSAY'
        assert frozen.raw_state() == before
        frozen.assert_unchanged()
        pipe.send(('ok', dict(variant=variant, subcase=scenario.subcase,
                              probes=4)))
    except BaseException:
        traceback.print_exc()
        pipe.send(('error',))
    finally:
        if frozen:
            frozen.close()
        if owned:
            owned.close()
        pipe.close()


def _d_child(pipe, cap, clone):
    """Family D equal-start policy pair preparation (worker-only)."""
    try:
        from development.evaluation.bootstrap import install_worker_adapters
        from development.evaluation.contracts import WorkerLaunch
        from development.evaluation.state import OwnedState
        from development.evaluation.adapters import construct_core
        from development.evaluation.coordinator import prepare_policy_pair
        launch = WorkerLaunch(cap, b'{"epsilon":0.15,"alpha":0.18}', 3, 'd' * 64)
        streams = install_worker_adapters(launch)
        core = construct_core(launch, streams, None)
        owned = OwnedState(cap, core.memory, core.memory.db.monitor)
        pair = prepare_policy_pair(owned, clone, seed=3, identity='d' * 64,
                                   close_owner=core.close)
        pipe.send(('ok', dict(
            pairing=pair['prediction_pairing'],
            initial_digest=pair['initial_digest'],
            seed_uuid=pair['seed'].uuid_identity,
            random_uuid=pair['random-eligible'].uuid_identity)))
    except BaseException:
        traceback.print_exc()
        pipe.send(('error',))
    finally:
        pipe.close()


def _spawn(target, args, checks, name, timeout=120):
    ctx = multiprocessing.get_context('spawn')
    parent, child = ctx.Pipe()
    process = ctx.Process(target=target, args=(child, *args),
                          name='seed-evaluation-worker')
    process.start()
    child.close()
    try:
        if not parent.poll(timeout):
            process.terminate()
            _check(checks, name, False, 'worker timed out')
            return None
        result = parent.recv()
        process.join(10)
        if result[0] != 'ok':
            _check(checks, name, False, 'worker reported an error')
            return None
        return result[1]
    finally:
        parent.close()
        if process.is_alive():
            process.terminate()


def _artifact_and_replay(base, checks):
    """Publish one technical artifact; replay it; retain a partial."""
    from tests.evaluation.test_artifacts import _record, _stage
    from development.evaluation.contracts import RunResult

    def load(name):
        return importlib.import_module('development.evaluation.' + name)

    plan_body = dict(
        schema='b10_analysis_plan_v1', experiment_id='technical-fixture',
        experiment_version=1, analysis_plan_version=1,
        members=[dict(id='member-0', family='A', scenario_version=2,
                      rule_version=2, protocol='PREQUENTIAL', variant='seed',
                      seed=0, training=0, measured=1)],
        metrics=[dict(id='prediction.numeric-mae', version=1)], seeds=[0],
        populations=[dict(id='all', phase='measured', action='all',
                          signal='load_ratio')],
        windows=[dict(id='whole', start=1, end=1, unit='ordinal')],
        baselines=[dict(id='persistence', version=1)], exclusions=[],
        eligibility='registered_support', coverage='all_opportunities',
        aggregation='ordered_fsum',
        standardization='equal_qualifying_actions',
        missing_rules='unavailable_with_reason', thresholds=[],
        questions=[dict(id='prediction', metrics=['prediction.numeric-mae'],
                        rule='descriptive_only',
                        reason='DESCRIPTIVE_ONLY_NO_CLASSIFICATION_RULE')],
        exploratory=True)
    artifact_base = base / 'artifacts'
    artifact_base.mkdir()
    root, frozen, artifacts = _stage(artifact_base, load, plan_body)
    payload = artifacts.assemble_payload(RunResult('COMPLETED', None),
                                         frozen, root)
    integrity = load('integrity')
    finalized = integrity.finalize_payload(payload, root)
    receipt = integrity.make_receipt(finalized, root)
    integrity.publish(finalized, receipt, root)
    reader = _load('reader').EvaluationReader(root)
    detail = reader.detail('a' * 32)
    _check(checks, 'artifact_published_and_read',
           detail.summary.execution.status == 'COMPLETED',
           detail.summary.execution.status)
    page = reader.events('a' * 32)
    _check(checks, 'recorded_replay_without_cognition',
           len(page.events) >= 1, f'{len(page.events)} events')
    # An interrupted technical run stays as retained partial evidence.
    partial_base = base / 'partial'
    partial_base.mkdir()
    root2, frozen2, artifacts2 = _stage(
        partial_base, load, plan_body,
        record=_record(status='INCOMPLETE', reason='STORAGE_INTERRUPTED'))
    payload2 = artifacts2.assemble_payload(
        RunResult('INCOMPLETE', 'STORAGE_INTERRUPTED'), frozen2, root2)
    _check(checks, 'interrupted_partial_evidence_retained',
           payload2.byte_length > 0, f'{payload2.byte_length} bytes')


def _failure_ladder(checks):
    """All-skipped attempts are accounted, never converted to samples."""
    prequential = _load('prequential')
    contracts = _load('contracts')

    class SkippingWorker:
        def __init__(self):
            self.calls = 0
            self.stopped = False

        def request(self, message):
            if message['operation'] == 'retry':
                return {'status': 'retry_scheduled'}
            self.calls += 1
            return dict(status='skipped', acked=False,
                        reason='stale_decision', delay_seconds=10)

        def stop(self, reason='OWNER_CANCELLED'):
            self.stopped = True

    worker = SkippingWorker()
    driver = prequential.PrequentialDriver(measured=8)
    result = driver.run(contracts.RunRequest('bounded'), worker)
    _check(checks, 'failed_run_status_honest',
           result.status == 'INCOMPLETE' and result.reason == 'LIMIT_REACHED',
           f'{result.status}/{result.reason}')
    _check(checks, 'skipped_attempts_never_samples',
           len(driver.events) == 0 and len(driver.skipped) == worker.calls == 8,
           f'{len(driver.skipped)} skipped, {len(driver.events)} events')


def run_all(base=None):
    checks = []
    families = {}
    base = Path(base) if base is not None else Path(
        tempfile.mkdtemp(prefix='seed-i30-scenario-'))
    base.mkdir(parents=True, exist_ok=True)
    base = base.resolve()
    root = _load('paths').EvaluationRoot.create(base)

    # Family A -- prequential protocol with durable score-before-learning.
    from development.evaluation.scenarios.stationary import (
        StationaryScenario)
    result, journal_lines, stages = _prequential(
        root, 'a' * 32, StationaryScenario(), measured=4)
    families['A'] = dict(protocol='PREQUENTIAL', status=result.status)
    _check(checks, 'a_prequential_completed', result.status == 'COMPLETED',
           result.status)
    _check(checks, 'a_score_journal_durable_prefix',
           journal_lines == 4, f'{journal_lines} journal lines')
    learning_stages = ('q', 'b1', 'b4', 'b5', 'b7', 'b8')
    _check(checks, 'a_actual_updates_confirmed',
           len(stages) == 4 and all(
               all(updates[stage]['status'] == 'confirmed'
                   for stage in learning_stages) and
               all(stage['status'] in ('confirmed', 'not_applicable')
                   for stage in updates.values())
               for updates in stages),
           f'{len(stages)} scored events; learning stages confirmed, '
           'inapplicable stages explicitly not_applicable')

    # Family B -- prequential run plus the rest-only shift literals.
    from development.evaluation.scenarios.shift import ShiftScenario
    result_b, journal_b, _ = _prequential(
        root, 'b' * 32, ShiftScenario(), measured=4)
    families['B'] = dict(protocol='PREQUENTIAL', status=result_b.status)
    _check(checks, 'b_prequential_completed', result_b.status == 'COMPLETED',
           result_b.status)
    _check(checks, 'b_exposure_recorded', journal_b == 4,
           f'{journal_b} journal lines')
    shift = ShiftScenario()
    key = lambda n: ('measured', 'default', n, 'pre')
    loads = {(action, when): shift.apply_action(action, key(when))['load_ratio']
             for action in ('rest', 'observe', 'reflect', 'consolidate')
             for when in (320, 321)}
    _check(checks, 'b_only_rest_changes_at_321',
           loads[('rest', 320)] == .4 and loads[('rest', 321)] == .55 and
           all(loads[(a, 320)] == loads[(a, 321)]
               for a in ('observe', 'reflect', 'consolidate')),
           'rest .4 -> .55 at ordinal 321; other actions unchanged')

    # Family A frozen assay in its own worker.
    cap_a = root.assign_learner('c' * 32, 0)
    counts = _spawn(_frozen_a_child, (cap_a,), checks, 'a_frozen_worker')
    if counts is not None:
        families['A']['frozen_probes'] = counts.get('a_frozen_probes')
        _check(checks, 'a_frozen_assay_probes',
               counts.get('a_frozen_probes') == 2, str(counts))
        _check(checks, 'frozen_state_unchanged', True,
               'worker asserted raw-state equality and assert_unchanged()')
    # Family C robustness variants, one evaluator-private worker each.
    subcases = {}
    for variant in ('cold', 'conflict', 'unavailable', 'stale'):
        cap_v = root.assign_learner('c-' + variant, 0)
        outcome = _spawn(_c_child, (cap_v, variant), checks,
                         'c_worker_' + variant)
        if outcome is not None:
            subcases[outcome['subcase']] = outcome['probes']
    families['C'] = subcases
    _check(checks, 'c_robustness_subcases',
           subcases == {'fresh': 4, 'contradictory': 4,
                        'unavailable': 4, 'stale': 4}, str(subcases))

    # Family D -- constrained scenario, guards, external utility, pair prep.
    from development.evaluation.scenarios.constrained import (
        ConstrainedScenario, task_utility)
    from seed.decision import constraints
    scenario_d = ConstrainedScenario()
    dkey = lambda n: ('measured', 'default', n, 'pre')
    guards_ok = True
    for n in range(1, 9):
        observation = scenario_d.initial_observation(dkey(n))
        if constraints(observation, 'observe') or constraints(observation, 'rest'):
            guards_ok = False
        for action in ('reflect', 'consolidate'):
            if bool(constraints(observation, action)) != (n != 1):
                guards_ok = False
    _check(checks, 'd_guards_preserved', guards_ok, 'guard matrix over 8 contexts')
    _check(checks, 'd_task_utility_external',
           [task_utility(scenario_d.initial_observation(dkey(1)), a)
            for a in ('reflect', 'consolidate', 'observe', 'rest')] ==
           [1, .75, .5, .25], 'registered literal utilities')
    cap_d = root.assign_learner('d' * 32, 0)
    clone_d = root.assign_learner('d' * 32, 1)
    pair = _spawn(_d_child, (cap_d, clone_d), checks, 'd_policy_pair')
    if pair is not None:
        families['D'] = dict(protocol='PREQUENTIAL', pairing=pair['pairing'])
        _check(checks, 'd_random_eligible_separate_trajectory',
               pair['seed_uuid'] != pair['random_uuid'] and
               pair['pairing'] == 'not_paired_divergent_policy_trajectories',
               'distinct role identities from one equal-start digest')

    _artifact_and_replay(base, checks)
    _failure_ladder(checks)

    passed = all(check['passed'] for check in checks)
    return dict(classification=CLASSIFICATION, passed=passed,
                families=families, checks=checks,
                bounds=dict(measured_per_run=4, frozen_probes=10,
                            roots='disposable only'))


def main():
    result = run_all()
    print(json.dumps(result, sort_keys=True))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
