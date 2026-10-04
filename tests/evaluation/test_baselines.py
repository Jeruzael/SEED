import json
import sys
import pytest

from development.evaluation.baselines import forecast_baselines
from development.evaluation.contracts import ContractError


def row(n, action='rest', delta=-.1, network=True):
    return dict(id=n, action=action, completed_at=float(n),
                state_before_json=json.dumps(dict(load_ratio=.5, network=False)),
                state_after_json=json.dumps(dict(load_ratio=.5+delta, network=network)))


def test_four_row_matched_fixture():
    from seed.predictor import Predictor
    history = (row(1), row(2), row(3, 'reflect', .1), row(4, 'reflect', .1))
    result = forecast_baselines({'load_ratio': .5, 'network': False}, 'rest', history, 4)
    for method in ('persistence', 'global-history'):
        signal = result[method]['signals']['load_ratio']
        assert signal['value'] == .5
        assert abs(signal['value'] - .4) == pytest.approx(.1)
    assert result['global-history']['signals']['load_ratio']['evidence_count'] == 4
    prediction = Predictor(None).predict_candidates({'load_ratio': .5}, ('rest',), snapshot=history).predictions['rest']
    assert prediction['signals']['load_ratio']['value'] == .4
    assert prediction['signals']['load_ratio']['evidence_count'] == 2
    assert result['global-history']['signals']['load_ratio']['source_ids'] == [4, 3, 2, 1]
    assert len(result['history']['source_digest']) == 64


def test_raw200_corruption_no_refill_and_cutoff():
    history = [row(n) for n in range(1, 202)]
    for n in range(3, 201):
        history[n-1]['state_after_json'] = '{bad'
    history[200] = row(201, delta=.5)  # the current target/future is excluded
    result = forecast_baselines({'load_ratio': .5}, 'rest', tuple(history), 200)
    assert result['history']['raw_rows_examined'] == 200
    signal = result['global-history']['signals']['load_ratio']
    assert signal['method'] == 'global_mean_delta' and signal['source_ids'] == [2, 1]
    history[199] = row(200, delta=.2)
    history[1]['state_after_json'] = '{bad'
    result = forecast_baselines({'load_ratio': .5}, 'rest', tuple(history), 200)
    assert result['global-history']['signals']['load_ratio']['value'] == pytest.approx(.55)
    # Row 1 is outside latest raw 200 at cutoff201, and cannot refill corruption.
    result = forecast_baselines({'load_ratio': .5}, 'rest', tuple(history), 201)
    assert result['history']['raw_ids'][-1] == 2
    assert result['global-history']['signals']['load_ratio']['source_ids'] == [201, 200]
    for source in history[1:]: source['state_after_json'] = '{bad'
    result = forecast_baselines({'load_ratio': .5}, 'rest', tuple(history), 201)
    assert result['global-history']['signals']['load_ratio']['method'] == 'persistence'
    assert result['global-history']['signals']['load_ratio']['value'] == .5


def test_boolean_probability_and_fallback():
    history = (row(1, network=True), row(2, network=False))
    result = forecast_baselines({'network': False}, 'observe', history, 2)
    assert 'probability_true' not in result['persistence']['signals']['network_reachable']
    signal = result['global-history']['signals']['network_reachable']
    assert signal['value'] is True and signal['probability_true'] == .5
    signal = forecast_baselines({'network': False}, 'rest', history, 1)['global-history']['signals']['network_reachable']
    assert signal['value'] is False and 'probability_true' not in signal
    assert signal['evidence_count'] == 0
    assert signal['candidate_source_ids'] == [1] and signal['candidate_usable_count'] == 1
    result = forecast_baselines({}, 'rest', history, 2)
    assert result['global-history']['signals']['network_reachable']['status'] == 'unavailable'
    assert result['global-history']['signals']['network_reachable']['value'] is None


def test_no_cutoff_is_empty_prior_and_bounds_are_explicit():
    result = forecast_baselines({'load_ratio': .5}, 'rest', (row(1), row(2)), None)
    assert result['history']['raw_rows_examined'] == 0
    assert result['global-history']['signals']['load_ratio']['value'] == .5
    for cutoff in (-1, True, 2**63, .5):
        with pytest.raises(ContractError): forecast_baselines({}, 'rest', (), cutoff)
    with pytest.raises(ContractError): forecast_baselines({}, 'unknown', (), 1)
    with pytest.raises(ContractError): forecast_baselines({}, 'rest', (row(1), row(1)), 2)


def test_baselines_have_no_truth_or_conditioned_predictor_dependency(monkeypatch):
    from seed.predictor import Predictor
    monkeypatch.setattr(Predictor, 'predict_candidates', lambda *a, **kw: (_ for _ in ()).throw(AssertionError('conditioned producer used')))
    for name in ('stationary', 'shift', 'evidence', 'constrained', 'private'):
        monkeypatch.setitem(sys.modules, 'development.evaluation.scenarios.' + name, None)
    result = forecast_baselines({'load_ratio': .5}, 'rest', (row(1), row(2)), 2)
    assert result['global-history']['signals']['load_ratio']['value'] == .4


def test_global_filters_and_clamps_match_real_b2_without_conditioning():
    from seed.predictor import Predictor
    history = (row(1), row(2), row(3), row(4))
    history[0]['state_before_json'] = '[]'
    history[1]['state_before_json'] = '{"load_ratio":true}'
    history[2]['state_before_json'] = '{"load_ratio":0,"disk_free_pct":99,"battery_pct":1}'
    history[2]['state_after_json'] = '{"load_ratio":3,"disk_free_pct":100,"battery_pct":0}'
    history[3]['state_before_json'] = history[2]['state_before_json']
    history[3]['state_after_json'] = history[2]['state_after_json']
    observation = {'load_ratio': .5, 'disk_free_pct': 100, 'battery_pct': 0}
    expected = Predictor(None).predict_candidates(observation, ('observe',), snapshot=history).predictions['observe']
    actual = forecast_baselines(observation, 'observe', history, 4)['global-history']['signals']
    for target, literal in [('load_ratio', 3.5), ('disk_free_pct', 100), ('battery_pct', 0)]:
        assert actual[target]['value'] == literal == expected['signals'][target]['value']
        assert actual[target]['evidence_count'] == 2
    assert actual['disk_free_pct']['clamped'] and actual['battery_pct']['clamped']
    assert not actual['load_ratio']['clamped']
