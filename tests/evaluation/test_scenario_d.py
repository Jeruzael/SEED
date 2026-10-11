import json
import multiprocessing
import pytest

from development.evaluation.scenarios.constrained import ConstrainedScenario, task_utility
from development.evaluation.coordinator import prepare_policy_pair
from development.evaluation.contracts import ContractError


def key(n):
    return ('measured', 'default', n, 'pre')


def test_d_contexts_and_synthetic_effects():
    scenario = ConstrainedScenario()
    observations = [scenario.initial_observation(key(n)) for n in range(1, 9)]
    assert observations[1]['load_ratio'] == .9
    assert observations[2]['battery_pct'] == 15 and observations[2]['charging'] is False
    assert observations[3]['disk_free_pct'] == 5
    assert observations[4]['battery_pct'] is None
    assert observations[5]['charging'] is None
    assert 'load_ratio' not in observations[6]
    assert 'disk_free_pct' not in observations[7]
    assert scenario.initial_observation(key(9)) == observations[0]
    for action, load, network in [('observe', .5, True), ('rest', .4, False), ('reflect', .6, True), ('consolidate', .55, False)]:
        outcome = scenario.apply_action(action, key(1))
        assert outcome['load_ratio'] == load and outcome['network'] is network
        assert outcome['battery_pct'] == 80 and outcome['disk_free_pct'] == 50
    assert 'load_ratio' not in scenario.apply_action('rest', key(7))
    assert 'disk_free_pct' not in scenario.apply_action('observe', key(8))
    scenario.initial_observation(key(128))
    with pytest.raises(ContractError): scenario.initial_observation(key(129))


def test_d_guards_and_boundaries():
    from seed.decision import constraints
    scenario = ConstrainedScenario()
    for n in range(1, 9):
        observation = scenario.initial_observation(key(n))
        assert not constraints(observation, 'observe') and not constraints(observation, 'rest')
        for action in ('reflect', 'consolidate'):
            assert bool(constraints(observation, action)) == (n != 1)
    common = scenario.initial_observation(key(1))
    for changes in ({'load_ratio': .8}, {'battery_pct': 20}, {'disk_free_pct': 10}):
        assert not constraints(dict(common, **changes), 'reflect')
    for changes in ({'load_ratio': .800001}, {'battery_pct': 19.999}, {'disk_free_pct': 9.999}):
        assert constraints(dict(common, **changes), 'reflect')


def test_task_utility_is_external():
    scenario = ConstrainedScenario()
    assert [task_utility(scenario.initial_observation(key(1)), a) for a in ('reflect', 'consolidate', 'observe', 'rest')] == [1, .75, .5, .25]
    assert [task_utility(scenario.initial_observation(key(2)), a) for a in ('reflect', 'consolidate', 'observe', 'rest')] == [0, 0, .25, 1]
    with pytest.raises(ContractError): task_utility({}, 'invented')


def _pair_child(pipe, cap, clone):
    try:
        from development.evaluation.bootstrap import install_worker_adapters
        from development.evaluation.contracts import WorkerLaunch
        from development.evaluation.state import OwnedState
        launch = WorkerLaunch(cap, b'{"epsilon":0.15,"alpha":0.18}', 3, 'd'*64)
        streams = install_worker_adapters(launch)
        from development.evaluation.adapters import construct_core
        core = construct_core(launch, streams, None)
        owned = OwnedState(cap, core.memory, core.memory.db.monitor)
        pair = prepare_policy_pair(owned, clone, seed=3, identity='d'*64, close_owner=core.close)
        pipe.send(('ok', pair))
    except BaseException:
        import traceback
        traceback.print_exc(); pipe.send(('error',))
    finally: pipe.close()


def test_random_eligible_real_records(tmp_path, foundation_module):
    from development.evaluation.channel import ChannelRouter
    root = foundation_module('paths').EvaluationRoot.create(tmp_path.resolve())
    cap = root.assign_learner('d'*32, 0); clone = root.assign_learner('d'*32, 1)
    ctx = multiprocessing.get_context('spawn'); parent, child = ctx.Pipe()
    process = ctx.Process(target=_pair_child, args=(child, cap, clone), name='seed-evaluation-worker')
    process.start(); child.close()
    try:
        assert parent.poll(15); result = parent.recv(); process.join(5)
        assert result[0] == 'ok', result
    finally:
        if process.is_alive(): process.terminate(); process.join(5)
        parent.close()
    pair = result[1]
    assert pair['seed'].rng_seed != pair['random-eligible'].rng_seed
    assert pair['initial_digest'] and pair['prediction_pairing'] == 'not_paired_divergent_policy_trajectories'
    trajectories = []
    for index, role in enumerate(('seed', 'random-eligible')):
        journal = foundation_module('checkpoint').ScoreJournal.create(root, str(index+1)*32)
        worker = foundation_module('worker').WorkerHandle.start(pair[role], channel=ChannelRouter(ConstrainedScenario(), journal=journal))
        records = []
        try:
            for ordinal in range(1, 9):
                value = worker.request({'operation': 'cycle', 'key': list(key(ordinal))})
                assert value['status'] == 'completed' and value['acked']
                selection = value['capture']['selection']
                assert selection['selected_action'] in selection['eligible_actions']
                if role == 'random-eligible':
                    assert selection['selection_mode'] == 'explore' and selection['epsilon'] == 1
                assert selection['alpha'] == .18
                update = value['updates']['q']
                assert update['status'] == 'confirmed'
                action = selection['selected_action']
                # Literal legacy rewards differ from external task utility,
                # particularly low disk: rest utility=1, legacy reward=-.2.
                rewards = {1: 0., 2: 1. if action == 'rest' else -.4,
                           3: 1.2 if action == 'rest' else -.6, 4: -.2,
                           5: 0., 6: 0., 7: .45 if action == 'observe' else 0., 8: 0.}
                old = selection['candidates'][action]['q_value']
                assert update['after']['value'] == pytest.approx(old + .18*(rewards[ordinal]-old))
                assert update['after']['visits'] == selection['candidates'][action]['visits'] + 1
                if ordinal == 1:
                    assert selection['history']['raw_rows_examined'] == 0
                    assert all(c['q_value'] == 0 for c in selection['candidates'].values())
                records.append(selection['selected_action'])
        finally: worker.stop(); journal.close()
        trajectories.append(records)
    assert trajectories[0] != trajectories[1]
