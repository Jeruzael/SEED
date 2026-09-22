"""Literal scoring expectations, independent of the evaluator implementation."""
import copy
import json
import socket
import sqlite3
import sys
import pytest


def payload(signals):
    return {'model':'transition_delta_v1','model_version':1,
            'horizon':'next_post_action_observation','action':'observe','signals':signals}


def predicted(value, **extra):
    return {'status':'predicted','value':value, **extra}


def evaluate(prediction, actual):
    from seed.prediction_error import evaluate_prediction
    result = evaluate_prediction(prediction, actual).to_dict()
    json.dumps(result, allow_nan=False)
    return result


@pytest.mark.parametrize('name,pred,actual,signed,absolute,normalized,method', [
    ('battery_pct',74,71,-3,3,.03,'percentage_range'),
    ('battery_pct',71,74,3,3,.03,'percentage_range'),
    ('battery_pct',0,100,100,100,1,'percentage_range'),
    ('disk_free_pct',80,80,0,0,0,'percentage_range'),
    ('disk_free_pct',20,10,-10,10,.1,'percentage_range'),
    ('load_ratio',.2,.4,.2,.2,.2,'bounded_relative'),
    ('load_ratio',4,5,1,1,.2,'bounded_relative'),
    ('load_ratio',5,4,-1,1,.2,'bounded_relative'),
    ('load_ratio',0,sys.float_info.max,sys.float_info.max,sys.float_info.max,1,'bounded_relative'),
    ('load_ratio',sys.float_info.max,0,-sys.float_info.max,sys.float_info.max,1,'bounded_relative')])
def test_numeric_error_rules(name,pred,actual,signed,absolute,normalized,method):
    result=evaluate(payload({name:predicted(pred)}), {name:actual})
    signal=result['signals'][name]
    assert signal['status']=='evaluated'
    assert signal['predicted']==pred and signal['actual']==actual
    assert signal['signed_error']==pytest.approx(signed)
    assert signal['absolute_error']==pytest.approx(absolute)
    assert signal['normalized_error']==pytest.approx(normalized)
    assert signal['scoring_method']==method
    assert result['aggregate']['coverage']==.25


@pytest.mark.parametrize('pred,actual,error',[(True,True,0),(False,False,0),(True,False,1),(False,True,1)])
def test_boolean_classification(pred,actual,error):
    result=evaluate(payload({'network_reachable':predicted(pred)}),{'network':actual})
    signal=result['signals']['network_reachable']
    assert signal['classification_error']==error and signal['correct'] is (error==0)
    assert signal['normalized_error']==error and signal['scoring_method']=='boolean_mismatch'
    assert 'probability_true' not in signal and 'brier_error' not in signal


@pytest.mark.parametrize('probability,when_true,when_false',[(0,1,0),(.25,.5625,.0625),(.5,.25,.25),(.75,.0625,.5625),(1,0,1)])
def test_boolean_brier(probability,when_true,when_false):
    for actual,expected in [(True,when_true),(False,when_false)]:
        result=evaluate(payload({'network_reachable':predicted(True,probability_true=probability)}),{'network':actual})
        signal=result['signals']['network_reachable']
        assert signal['brier_error']==expected and signal['normalized_error']==expected
        assert signal['classification_error']==(0 if actual else 1)
        assert signal['scoring_method']=='boolean_brier'


@pytest.mark.parametrize('bad',[None,True,'0.5',-1,2,float('nan'),float('inf'),10**1000])
def test_invalid_probability_uses_classification_without_echoing_invalid_value(bad):
    signal=evaluate(payload({'network_reachable':predicted(True,probability_true=bad)}),{'network':False})['signals']['network_reachable']
    assert signal['normalized_error']==1 and signal['scoring_method']=='boolean_mismatch'
    assert 'probability_true' not in signal and 'brier_error' not in signal


@pytest.mark.parametrize('bad',[None,True,'4',{},[],float('nan'),float('inf'),-1,101,10**1000])
def test_invalid_numeric_pairs_are_not_counted_as_success(bad):
    for prediction,actual,reason in [(predicted(bad),74,'invalid_prediction'),
                                      (predicted(74),bad,'actual_unavailable')]:
        result=evaluate(payload({'battery_pct':prediction}),{'battery_pct':actual})
        signal=result['signals']['battery_pct']
        assert signal=={'status':'not_evaluated','reason':reason}
        assert result['aggregate']=={'status':'unavailable','evaluated_signals':0,'target_signals':4,
                                     'coverage':0,'mean_normalized_error':None,'accuracy_score':None}


def test_unavailable_prediction_precedes_missing_actual_and_missing_keys_are_explicit():
    result=evaluate(payload({'battery_pct':{'status':'unavailable','reason':'missing_current_value'},
                             'load_ratio':predicted(.2)}),{})
    assert result['signals']['battery_pct']['reason']=='prediction_unavailable'
    assert result['signals']['load_ratio']['reason']=='actual_unavailable'
    assert result['signals']['disk_free_pct']['reason']=='invalid_prediction'
    assert result['aggregate']['status']=='unavailable'


@pytest.mark.parametrize('bad',[0,1,None,'true',[],{},float('nan')])
def test_network_requires_actual_booleans_on_both_sides(bad):
    a=evaluate(payload({'network_reachable':predicted(bad)}),{'network':True})
    b=evaluate(payload({'network_reachable':predicted(True)}),{'network':bad})
    assert a['signals']['network_reachable']['reason']=='invalid_prediction'
    assert b['signals']['network_reachable']['reason']=='actual_unavailable'


@pytest.mark.parametrize('bad',[None,[],{},'oops','null','[]','{"signals":null}',
    '['*2000+'0'+']'*2000,' '*70000], ids=['none','list','dict','bad_json','null','array','bad_signals','deep','oversized'])
def test_malformed_whole_payload_is_safe(bad):
    result=evaluate(bad,{'battery_pct':70})
    assert result['aggregate']['status']=='unavailable'
    assert all(s=={'status':'not_evaluated','reason':'invalid_prediction'} for s in result['signals'].values())


@pytest.mark.parametrize('field,value',[('model','unknown'),('model_version',2),('model_version',True),
                                      ('horizon','next_cycle'),('signals',[])])
def test_unknown_contract_is_not_silently_reinterpreted(field,value):
    p=payload({'battery_pct':predicted(70)})
    p[field]=value
    assert evaluate(p,{'battery_pct':70})['aggregate']['status']=='unavailable'


def test_full_and_partial_aggregates_track_coverage_separately():
    p=payload({'battery_pct':predicted(50),'disk_free_pct':predicted(50),
               'load_ratio':predicted(.2),'network_reachable':predicted(True,probability_true=.5)})
    full=evaluate(p,{'battery_pct':60,'disk_free_pct':70,'load_ratio':.4,'network':False})
    assert full['evaluator']=='prediction_error_v1' and full['evaluator_version']==1
    assert full['prediction_model']=='transition_delta_v1' and full['prediction_model_version']==1
    assert full['horizon']=='next_post_action_observation'
    assert full['aggregate']=={'status':'evaluated','evaluated_signals':4,'target_signals':4,
                              'coverage':1,'mean_normalized_error':.1875,'accuracy_score':.8125}
    partial=evaluate(p,{'battery_pct':50,'disk_free_pct':50})['aggregate']
    assert partial['coverage']==.5 and partial['evaluated_signals']==2
    assert partial['mean_normalized_error']==0 and partial['accuracy_score']==1
    assert evaluate(p,{})['aggregate']['accuracy_score'] is None


def test_serialized_payload_and_extra_fields_do_not_change_scores():
    p=payload({'battery_pct':predicted(70,confidence=.95,confidence_kind='evidence_support')})
    before=copy.deepcopy(p)
    assert evaluate(json.dumps(p),{'battery_pct':69})==evaluate(p,{'battery_pct':69})
    p['ignored']=p  # Extra cyclic data must not be traversed/copied by scoring.
    p['signals']['unrecognized']=object()
    result=evaluate(p,{'battery_pct':69,'ignored':object()})
    assert result['signals']['battery_pct']['absolute_error']==1
    assert len(result['signals'])==4
    assert p['signals']['battery_pct']==before['signals']['battery_pct']


def test_evaluator_is_pure_without_storage_sensing_or_network(home,monkeypatch):
    from seed.memory import Memory
    m=Memory(home/'memory.sqlite3')
    try:
        before=list(m.db.iterdump())
        p=payload({'battery_pct':predicted(70)})
        actual={'battery_pct':69}
        original=copy.deepcopy((p,actual))
        def forbidden(*args,**kwargs): raise AssertionError('evaluator performed IO')
        monkeypatch.setattr(sqlite3,'connect',forbidden)
        monkeypatch.setattr(socket,'socket',forbidden)
        monkeypatch.setattr(socket,'create_connection',forbidden)
        monkeypatch.setattr(socket,'getaddrinfo',forbidden)
        monkeypatch.setattr('seed.body.Body.perceive',forbidden)
        m.db.set_authorizer(lambda *args:sqlite3.SQLITE_DENY)
        try:
            assert evaluate(p,actual)==evaluate(p,actual)
        finally:
            m.db.set_authorizer(None)
        assert (p,actual)==original
        assert list(m.db.iterdump())==before
    finally:
        m.close()
