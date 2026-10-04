import pytest
from development.evaluation.contracts import Population
from development.evaluation.metrics.prediction import measure_prediction
from development.evaluation.metrics.registry import measurement_data
from .test_prediction_metrics import evidence, frozen


def prechange():
    return evidence(321, 'observe', candidates={'rest': {'signals': {'load_ratio': dict(method='action_mean_delta', evidence_count=2, status='predicted', value=.4)}}})


def test_adaptation_exposure_rules(tmp_path, plan_body):
    plan = frozen(tmp_path, plan_body, family='B')
    rows = (prechange(),) + tuple(evidence(330+n*3, prediction=.55, actual=.55) for n in range(15))
    result = measure_prediction('prediction.adaptation-delay', rows, Population('all',('member-0',)), plan)
    assert result.state == 'MEASURED'
    assert result.value['event'] == 'observed'
    assert result.value['rest_exposures'] == 15
    assert result.value['completed_transition_delay'] == 52
    assert [w['end_exposure'] for w in result.value['confirmation_windows']] == [5,10,15]


def test_fallback_and_missing_stay_in_exposure_positions(tmp_path, plan_body):
    plan = frozen(tmp_path, plan_body, family='B')
    rows = [prechange()] + [evidence(322+n, prediction=.55, actual=.55) for n in range(20)]
    rows[3] = evidence(324, prediction=.55, actual=.55, method='persistence', support=0)
    result = measure_prediction('prediction.adaptation-delay', tuple(rows), Population('all',('member-0',)), plan)
    assert result.value['rest_exposures'] == 20
    assert result.value['confirmation_windows'][0]['start_exposure'] == 6
    rows[8] = evidence(329, prediction=None, actual=.55)
    unavailable = measure_prediction('prediction.adaptation-delay', tuple(rows), Population('all',('member-0',)), plan)
    assert unavailable.state == 'UNAVAILABLE' and unavailable.reason == 'INSUFFICIENT_EVIDENCE'
    assert measurement_data(unavailable)['observed_rest_exposures'] == 20


def test_insufficient_prechange_and_right_censoring(tmp_path, plan_body):
    plan = frozen(tmp_path, plan_body, family='B')
    population = Population('all',('member-0',))
    rows = tuple(evidence(322+n, prediction=.4, actual=.55) for n in range(15))
    result = measure_prediction('prediction.adaptation-delay', rows, population, plan)
    assert result.reason == 'INSUFFICIENT_PRECHANGE_EVIDENCE'
    result = measure_prediction('prediction.adaptation-delay', (prechange(),)+rows, population, plan)
    assert result.state == 'MEASURED' and result.value['event'] == 'not_observed'
    assert result.value['right_censored_rest_exposures'] == 15
    assert result.value['registered_postshift_transition_horizon'] == 480


@pytest.mark.parametrize('k,predicted,error', [(0,.4,.15),(10,.475,.075),(20,.55,0)])
def test_rest_window_and_lifetime_literals(k, predicted, error):
    import json
    from seed.predictor import Predictor
    from .test_baselines import row
    history = tuple(row(n, delta=-.1 if n <= 20-k else .05) for n in range(1,21))
    signal = Predictor(None).predict_candidates({'load_ratio':.5},('rest',),snapshot=history).predictions['rest']['signals']['load_ratio']
    assert signal['value'] == pytest.approx(predicted)
    assert abs(signal['value']-.55) == pytest.approx(error)


def test_other_actions_evict_old_rest_and_current_is_excluded():
    from .test_baselines import row
    from development.evaluation.baselines import forecast_baselines
    from seed.predictor import Predictor
    history = tuple([row(1), row(2)] + [row(n, 'observe', 0) for n in range(3,203)] + [row(203, delta=.05)])
    prior = forecast_baselines({'load_ratio':.5},'rest',history,202)
    assert prior['history']['raw_ids'] == list(range(202,2,-1))
    bounded = tuple(r for r in history if r['id'] in prior['history']['raw_ids'])
    signal = Predictor(None).predict_candidates({'load_ratio':.5},('rest',),snapshot=bounded).predictions['rest']['signals']['load_ratio']
    assert signal['method'] == 'global_mean_delta' and signal['value'] == .5


@pytest.mark.parametrize('defect',['action','method','comparison','signal','window','variant','phase'])
def test_adaptation_preregistered_scope_cannot_mislabel_rest_evidence(tmp_path,plan_body,defect):
    import copy
    from development.evaluation.analysis import validate_plan,freeze_plan,expand_inventory
    from .test_analysis import ClosedRoot
    body=copy.deepcopy(plan_body)
    body['metrics']=[dict(id='prediction.adaptation-delay',version=2)]
    body['questions'][0]['metrics']=['prediction.adaptation-delay']
    body['members'][0].update(family='B',scenario_version=2,rule_version=2,measured=800)
    body['populations'][0].update(signal='load_ratio',method='seed',comparison=None,stratum='all_methods')
    body['windows']=[dict(id='whole',start=1,end=800,unit='ordinal')]
    if defect=='action':body['populations'][0]['action']='observe'
    elif defect=='method':body['populations'][0]['method']='persistence'
    elif defect=='comparison':body['populations'][0]['comparison']='persistence'
    elif defect=='signal':body['populations'][0]['signal']='battery_pct'
    elif defect=='window':body['windows'][0].update(start=321,end=360)
    elif defect=='variant':body['populations'][0]['variant']='stale'
    elif defect=='phase':body['populations'][0]['phase']='probe'
    admitted=validate_plan(body)
    plan=freeze_plan(admitted,ClosedRoot(tmp_path))
    rows=(prechange(),)+tuple(evidence(700+n,prediction=.55,actual=.55) for n in range(15))
    result=measure_prediction('prediction.adaptation-delay',rows,Population('all',('member-0',)),plan)
    assert result.state=='NOT_EVALUATED' and result.value is None
    assert not __import__('json').loads(expand_inventory(admitted)[0].body)['applicable']


def test_rest_only_descriptor_keeps_boundary_candidate_and_horizon(tmp_path,plan_body):
    import copy
    body=copy.deepcopy(plan_body);body['populations'][0]['action']='rest'
    plan=frozen(tmp_path,body,family='B')
    rows=(prechange(),)+tuple(evidence(700+n,prediction=.55,actual=.55) for n in range(15))
    rows+=tuple(evidence(801+n,prediction=.55,actual=.55) for n in range(15))
    result=measure_prediction('prediction.adaptation-delay',rows,Population('all',('member-0',)),plan)
    assert result.value['rest_exposures']==15 and result.value['completed_transition_delay']==394
    detail=measurement_data(result)
    assert detail['observed_rest_exposures']==15 and detail['measurement_action']=='rest'
    assert detail['qualification_ordinal']==321 and detail['measurement_method']=='seed_action_mean_delta_support_at_least_2'
