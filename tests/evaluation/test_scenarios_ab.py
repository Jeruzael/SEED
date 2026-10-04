import pytest

from development.evaluation.contracts import ContractError
from development.evaluation.scenarios.stationary import StationaryScenario, validate_action_effects
from development.evaluation.scenarios.shift import ShiftScenario


def key(n, phase='measured'):
    return (phase, 'default', n, 'pre')


def test_a_distinct_action_guard():
    with pytest.raises(ContractError):
        validate_action_effects(dict.fromkeys(('observe', 'rest', 'reflect', 'consolidate'), .1))


@pytest.mark.parametrize('action,load', [('observe', .50), ('rest', .40), ('reflect', .60), ('consolidate', .55)])
def test_a_literal_outcome_and_detached_reset(action, load):
    scenario = StationaryScenario()
    initial = scenario.initial_observation(key(1))
    assert initial == dict(battery_pct=80, charging=False, load_ratio=.5, disk_free_pct=50, network=False, local_hour=12)
    initial['load_ratio'] = 1.5
    outcome = scenario.apply_action(action, key(1))
    assert outcome == dict(battery_pct=79.75, charging=False, load_ratio=load, disk_free_pct=49.95, network=True, local_hour=12)
    assert scenario.initial_observation(key(2))['load_ratio'] == .5
    assert scenario.reset_event(key(2))['kind'] == 'exogenous_reset'


def test_b_only_rest_changes_at321():
    scenario = ShiftScenario()
    for action, before, after in [('rest', .4, .55), ('observe', .5, .5), ('reflect', .6, .6), ('consolidate', .55, .55)]:
        assert scenario.apply_action(action, key(320))['load_ratio'] == before
        assert scenario.apply_action(action, key(321))['load_ratio'] == after
    assert set(scenario.initial_observation(key(321))) == {'battery_pct', 'charging', 'load_ratio', 'disk_free_pct', 'network', 'local_hour'}
    assert 'rest-shift-v2' in scenario.evaluator_view().body.decode()


def test_phase_lengths_and_exposure():
    online = StationaryScenario()
    online.initial_observation(key(400))
    with pytest.raises(ContractError):
        online.initial_observation(key(401))
    frozen = StationaryScenario('FROZEN_SELECTION_ASSAY')
    frozen.initial_observation(key(320, 'training'))
    frozen.initial_observation(key(80, 'probe'))
    for k in (key(321, 'training'), key(81, 'probe'), key(1)):
        with pytest.raises(ContractError):
            frozen.initial_observation(k)
    ShiftScenario().initial_observation(key(800))
    with pytest.raises(ContractError):
        ShiftScenario().initial_observation(key(801))
    # The engine reacts to the caller's actual selected action; even a wholly
    # unsupported rest trajectory remains observe, with no replacement action.
    assert [online.apply_action('observe', key(n))['load_ratio'] for n in range(1, 5)] == [.5] * 4


def test_invalid_action_and_phase_never_produce_outcome():
    with pytest.raises(ContractError):
        StationaryScenario().apply_action('invented', key(1))
    with pytest.raises(ContractError):
        ShiftScenario().initial_observation(key(1, 'training'))


def test_real_selection_has_no_forced_exposure(tmp_path, foundation_module):
    import json
    from development.evaluation.contracts import WorkerLaunch
    from development.evaluation.channel import ChannelRouter
    root = foundation_module('paths').EvaluationRoot.create(tmp_path.resolve())
    cap = root.assign_learner('a'*32, 0)
    journal = foundation_module('checkpoint').ScoreJournal.create(root, 'a'*32)
    worker = foundation_module('worker').WorkerHandle.start(
        WorkerLaunch(cap, b'{"epsilon":0.15,"alpha":0.18}', 3, 'a'*64),
        channel=ChannelRouter(StationaryScenario(), journal=journal))
    try:
        result = worker.request({'operation': 'cycle', 'key': list(key(1))})
        assert result['status'] == 'completed' and result['acked']
        detail = result['capture']
        if isinstance(detail, str):
            detail = json.loads(detail)
        assert detail['selection']['selected_action'] in ('observe', 'reflect', 'consolidate', 'rest')
        assert detail['selection']['history']['raw_rows_examined'] == 0
    finally:
        worker.stop()
        journal.close()
