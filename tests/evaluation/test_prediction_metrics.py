import copy
import json
import pytest

from development.evaluation.contracts import CompletedEvidence, Population
from development.evaluation.metrics.prediction import measure_prediction
from development.evaluation.metrics.registry import measurement_data
from .test_analysis import ClosedRoot


def frozen(tmp_path, plan_body, *, family='A', signal='load_ratio', comparison=None, stratum='all_methods'):
    from development.evaluation.analysis import validate_plan, freeze_plan
    from development.evaluation.registry import METRICS, REGISTRIES
    plan_body = copy.deepcopy(plan_body)
    plan_body['metrics'] = [{'id': m, 'version': REGISTRIES['metric'][m]} for m in METRICS]
    plan_body['members'][0].update(family=family, scenario_version=2, rule_version=2, measured=800 if family=='B' else 400)
    plan_body['populations'][0].update(signal=signal, method='seed', comparison=comparison, stratum=stratum)
    plan_body['windows'] = [dict(id='whole', start=1, end=800 if family=='B' else 400, unit='ordinal')]
    return freeze_plan(validate_plan(plan_body), ClosedRoot(tmp_path))


def evidence(n, action='rest', *, prediction=.5, actual=.4, method='action_mean_delta', support=2,
             baseline=.5, target='load_ratio', probability=None, candidates=None):
    signal = dict(status='predicted' if prediction is not None else 'unavailable', value=prediction,
                  method=method, evidence_count=support, confidence=min(.95,support/20))
    if probability is not None: signal['probability_true'] = probability
    body = dict(selected_action=action, prediction={'signals': {target: signal}},
                state_after={'network' if target=='network_reachable' else target: actual},
                history_cutoff_id=n-1, candidate_predictions=candidates or {},
                baselines={'persistence': {'signals': {target: dict(status='predicted' if baseline is not None else 'unavailable', value=baseline, method='persistence', evidence_count=0)}}})
    return CompletedEvidence(('measured','default',n,'update'), json.dumps(body).encode())


def test_literal_metrics_and_support(tmp_path, plan_body):
    plan = frozen(tmp_path, plan_body)
    data = (evidence(1, prediction=.9, actual=.4, support=200), evidence(2, prediction=.5, actual=.4))
    population = Population('all', ('member-0',))
    measured = measure_prediction('prediction.numeric-mae', data, population, plan)
    assert measured.state == 'MEASURED' and measured.value == pytest.approx(.3)
    payload = measurement_data(measured)
    assert payload['numerator'] == pytest.approx(.6) and payload['denominator'] == 2
    assert payload['source_ordinals'] == [1,2] and payload['plan_digest'] == plan.digest
    assert measure_prediction('prediction.numeric-normalized-mae', data, population, plan).value == pytest.approx(.3)
    zero = measure_prediction('prediction.numeric-mae', (evidence(1, prediction=.4),), population, plan)
    assert zero.value == 0 and zero.state == 'MEASURED'
    missing = measure_prediction('prediction.numeric-mae', (), population, plan)
    assert missing.value is None and missing.state == 'UNAVAILABLE' and missing.reason


def test_percent_normalization_unclipped(tmp_path, plan_body):
    plan = frozen(tmp_path, plan_body, signal='battery_pct')
    result = measure_prediction('prediction.numeric-normalized-mae',
        (evidence(1, prediction=90, actual=40, target='battery_pct'),), Population('all', ('member-0',)), plan)
    assert result.value == .5
    # Registered load scale is one, not B3's bounded_relative denominator.
    other = tmp_path/'load'; other.mkdir()
    plan = frozen(other, plan_body)
    result = measure_prediction('prediction.numeric-normalized-mae',
        (evidence(1, prediction=2, actual=0),), Population('all', ('member-0',)), plan)
    assert result.value == 2


def test_brier_requires_genuine_probability(tmp_path, plan_body):
    plan = frozen(tmp_path, plan_body, signal='network')
    population = Population('all', ('member-0',))
    real = evidence(1, prediction=True, actual=False, target='network_reachable', probability=.75, method='action_boolean_frequency')
    assert measure_prediction('prediction.boolean-brier', (real,), population, plan).value == .5625
    confidence_only = evidence(1, prediction=True, actual=False, target='network_reachable', support=20)
    result = measure_prediction('prediction.boolean-brier', (confidence_only,), population, plan)
    assert result.state == 'UNAVAILABLE' and result.value is None
    assert measure_prediction('prediction.boolean-accuracy', (confidence_only,), population, plan).value == 0


def test_paired_intersection_coverage_and_reasons(tmp_path, plan_body):
    plan = frozen(tmp_path, plan_body, comparison='persistence')
    rows = (evidence(1, prediction=.4), evidence(2, prediction=None),
            evidence(3, prediction=.9, baseline=None), evidence(4, prediction=None, baseline=None))
    result = measure_prediction('prediction.numeric-mae', rows, Population('all', ('member-0',)), plan)
    data = measurement_data(result)
    assert result.value == 0 and data['denominator'] == 1
    assert data['coverage']['seed'] == .5 and data['coverage']['persistence'] == .5
    assert data['eligibility_cross_tab'] == {'both':1,'seed_only':1,'baseline_only':1,'neither':1}
    assert sum(data['reason_cross_tab'].values()) == 4
    assert data['exclusions'] == 3 and data['action_strata']['rest']['opportunities'] == 4


def test_paired_windows_and_standardization(tmp_path, plan_body):
    plan = frozen(tmp_path, plan_body, comparison='persistence')
    rows = []
    for n in range(1, 16): rows.append(evidence(n, 'rest' if n<=10 else 'reflect', prediction=.6 if n<=10 else 1., actual=.4))
    for n in range(361, 371): rows.append(evidence(n, 'rest' if n<=365 else 'reflect', prediction=.5, actual=.4))
    result = measure_prediction('prediction.window-change', tuple(rows), Population('all', ('member-0',)), plan)
    data = measurement_data(result)
    assert data['qualifying_actions'] == ['reflect','rest']
    assert data['standardized']['early'] == pytest.approx(.4)
    assert data['standardized']['late'] == pytest.approx(.1)
    assert result.value == pytest.approx(.3)
    assert data['natural_action_mix']['early'] == pytest.approx(1/3)
    absent = measure_prediction('prediction.window-change', tuple(rows[:10]), Population('all', ('member-0',)), plan)
    assert absent.state == 'UNAVAILABLE' and absent.value is None


def test_unregistered_method_or_forged_plan_rejected(tmp_path, plan_body):
    from dataclasses import replace
    from development.evaluation.contracts import ContractError
    plan = frozen(tmp_path, plan_body)
    with pytest.raises(ContractError):
        measure_prediction('prediction.numeric-mae', (), Population('all',('member-0',)), replace(plan,digest='0'*64))


def test_mismatched_baseline_cutoff_and_duplicate_target_rejected(tmp_path, plan_body):
    from development.evaluation.contracts import ContractError
    plan = frozen(tmp_path, plan_body, comparison='persistence')
    point = evidence(1)
    body = json.loads(point.body)
    body['baselines'].update(history={'cutoff_transition_id': 1}, action='rest')
    wrong = CompletedEvidence(point.key, json.dumps(body).encode())
    population = Population('all',('member-0',))
    with pytest.raises(ContractError):
        measure_prediction('prediction.numeric-mae', (wrong,), population, plan)
    with pytest.raises(ContractError):
        measure_prediction('prediction.numeric-mae', (point,point), population, plan)


def test_action_conditioning_stratum_keeps_fallback_as_exclusion(tmp_path, plan_body):
    plan = frozen(tmp_path, plan_body, comparison='persistence', stratum='action_mean')
    result = measure_prediction('prediction.numeric-mae',
        (evidence(1),evidence(2, method='global_mean_delta', support=200)), Population('all',('member-0',)), plan)
    data = measurement_data(result)
    assert data['denominator'] == 1 and data['opportunities'] == 2
    assert data['eligibility_cross_tab']['baseline_only'] == 1
    assert data['methods'] == {'action_mean_delta':1,'global_mean_delta':1}
    assert result.state == 'UNAVAILABLE'  # fewer than five formal stratum targets


def test_actual_worker_capture_is_measured_without_recomputing_prediction(tmp_path, plan_body, foundation_module):
    from development.evaluation.contracts import WorkerLaunch
    from development.evaluation.channel import ChannelRouter
    from development.evaluation.scenarios.stationary import StationaryScenario
    plan_path = tmp_path/'plan'; plan_path.mkdir()
    plan = frozen(plan_path, plan_body)
    root = foundation_module('paths').EvaluationRoot.create(tmp_path.resolve())
    cap = root.assign_learner('e'*32,0)
    journal = foundation_module('checkpoint').ScoreJournal.create(root,'e'*32)
    worker = foundation_module('worker').WorkerHandle.start(WorkerLaunch(cap,b'{"epsilon":0.15}',3,'e'*64),
        channel=ChannelRouter(StationaryScenario(),journal=journal))
    try:
        value = worker.request({'operation':'cycle','key':['measured','default',1,'pre']})
        assert value['status'] == 'completed' and value['acked']
        point = CompletedEvidence(('measured','default',1,'update'),json.dumps(value).encode())
        result = measure_prediction('prediction.numeric-mae',(point,),Population('all',('member-0',)),plan)
        action = value['capture']['selected_action']
        assert result.value == pytest.approx({'observe':0.,'rest':.1,'reflect':.1,'consolidate':.05}[action])
        assert measurement_data(result)['source_ordinals'] == [1]
    finally:
        worker.stop(); journal.close()
