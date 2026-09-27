"""Inference against real temporary SQLite history, with hand-calculated results."""
import json
import socket
import sqlite3
import sys
import pytest
from seed.memory import Memory

CURRENT = {'battery_pct':50, 'load_ratio':.5, 'disk_free_pct':40, 'network':False}


@pytest.fixture
def memory(home):
    m = Memory(home / 'memory.sqlite3')
    yield m
    m.close()


def history(m, before, after, action='observe'):
    # Raw fixture writes intentionally allow corrupt historical JSON for rejection tests.
    before_json = before if isinstance(before, str) else json.dumps(before)
    after_json = after if isinstance(after, str) else json.dumps(after)
    with m.db:
        episode = m.db.execute("INSERT INTO episodes(ts,event,state_json) VALUES(1,'experience',?)", (before_json,))
        m.db.execute('''INSERT INTO transitions(episode_id,started_at,completed_at,state_before_json,
                        action,state_after_json,outcome_json,legacy_reward) VALUES(?,1,2,?,?,?,'{}',0)''',
                     (episode.lastrowid,before_json,action,after_json))


def predict(m, state=None, action='observe'):
    from seed.predictor import Predictor
    return Predictor(m).predict(CURRENT if state is None else state, action).to_dict()


def test_cold_start_contract_and_repeatability(memory):
    result = predict(memory)
    assert result['model'] == 'transition_delta_v1' and result['model_version'] == 1
    assert result['horizon'] == 'next_post_action_observation' and result['action'] == 'observe'
    expected = {'battery_pct':50,'load_ratio':.5,'disk_free_pct':40,'network_reachable':False}
    assert set(result['signals']) == set(expected)
    for name,value in expected.items():
        signal = result['signals'][name]
        assert signal['value'] == value and signal['status'] == 'predicted'
        assert signal['method'] == 'persistence'
        assert signal['evidence_count'] == 0 and signal['confidence'] == 0
        assert signal['confidence_kind'] == 'evidence_support'
    assert predict(memory) == result
    json.dumps(result, allow_nan=False)


def test_numeric_action_conditioning_and_global_fallback(memory):
    for old,new in [(80,79),(70,68),(60,59)]:
        history(memory, {'battery_pct':old}, {'battery_pct':new})
    for old,new in [(80,84),(70,72)]:
        history(memory, {'battery_pct':old}, {'battery_pct':new}, 'reflect')
    observed = predict(memory)['signals']['battery_pct']
    assert observed['value'] == pytest.approx(48+2/3)
    assert observed['method'] == 'action_mean_delta' and observed['evidence_count'] == 3
    assert observed['confidence'] == .15
    reflected = predict(memory, action='reflect')['signals']['battery_pct']
    assert reflected['value'] == 53 and reflected['evidence_count'] == 2
    global_ = predict(memory, action='rest')['signals']['battery_pct']
    assert global_['value'] == pytest.approx(50.4)
    assert global_['method'] == 'global_mean_delta' and global_['evidence_count'] == 5


def test_minimum_evidence_is_per_signal_and_falls_through(memory):
    history(memory, {'battery_pct':80,'load_ratio':1}, {'battery_pct':78,'load_ratio':2})
    assert predict(memory)['signals']['battery_pct']['method'] == 'persistence'
    assert predict(memory)['signals']['battery_pct']['evidence_count'] == 0
    history(memory, {'battery_pct':80}, {'battery_pct':76}, 'rest')
    signals = predict(memory)['signals']
    assert signals['battery_pct']['method'] == 'global_mean_delta'
    assert signals['battery_pct']['value'] == 47
    assert signals['load_ratio']['method'] == 'persistence'


@pytest.mark.parametrize('values,probability,expected', [([True,False],.5,True),
    ([True,False,False],1/3,False),([True,True,False],2/3,True)])
def test_network_boolean_frequency_and_tie(memory, values, probability, expected):
    for value in values:
        history(memory, {'network':False}, {'network':value})
    signal = predict(memory)['signals']['network_reachable']
    assert signal['method'] == 'action_boolean_frequency'
    assert signal['probability_true'] == probability
    assert signal['value'] is expected and signal['evidence_count'] == len(values)
    assert predict(memory, action='rest')['signals']['network_reachable']['method'] == 'global_boolean_frequency'


@pytest.mark.parametrize('state', [{}, {'battery_pct':None,'load_ratio':'bad','disk_free_pct':-1,'network':0},
    {'battery_pct':True,'load_ratio':float('nan'),'disk_free_pct':float('inf'),'network':'false'},
    {'battery_pct':101,'load_ratio':-1,'disk_free_pct':101,'network':None}])
def test_unusable_current_signals_are_unavailable_even_with_history(memory, state):
    for _ in range(2): history(memory, CURRENT, CURRENT)
    for signal in predict(memory, state)['signals'].values():
        assert signal['status'] == 'unavailable'
        assert signal['evidence_count'] == 0
        assert 'value' not in signal and 'probability_true' not in signal


@pytest.mark.parametrize('bad', [None, True, '80', [], {}, -1, 101, float('nan'), float('inf')])
def test_invalid_numeric_history_is_skipped_per_signal(memory, bad):
    history(memory, {'battery_pct':bad}, {'battery_pct':60})
    history(memory, {'battery_pct':60}, {'battery_pct':bad})
    for _ in range(2): history(memory, {'battery_pct':80}, {'battery_pct':79,'extra':'ignored'})
    signal = predict(memory)['signals']['battery_pct']
    assert signal['evidence_count'] == 2 and signal['value'] == 49


@pytest.mark.parametrize('before,after', [('oops','{}'), ('{}','oops'), ('[]','{}'),
    ('{}','null'), ({},{'battery_pct':50}), ({'battery_pct':50},{}),
    ({'load_ratio':None},{'load_ratio':1})])
def test_missing_or_malformed_history_falls_back(memory, before, after):
    history(memory, before, after)
    history(memory, before, after)
    assert all(s['method']=='persistence' for s in predict(memory)['signals'].values())


def test_network_rejects_non_boolean_history(memory):
    for bad in [0,1,None,'true',[],{}]: history(memory, {}, {'network':bad})
    history(memory, {}, {'network':True})
    history(memory, {}, {'network':False})
    signal = predict(memory)['signals']['network_reachable']
    assert signal['evidence_count'] == 2 and signal['probability_true'] == .5


@pytest.mark.parametrize('name,current,before,after,expected', [
    ('battery_pct',1,90,80,0), ('battery_pct',99,80,90,100),
    ('disk_free_pct',2,80,70,0), ('disk_free_pct',98,70,80,100),
    ('load_ratio',.1,2,1,0), ('load_ratio',1e308,0,1e308,sys.float_info.max)])
def test_numeric_bounds_and_finite_overflow(memory, name, current, before, after, expected):
    for _ in range(2): history(memory, {name:before}, {name:after})
    result = predict(memory, {name:current})
    assert result['signals'][name]['value'] == expected
    assert result['signals'][name]['clamped'] is True
    json.dumps(result, allow_nan=False)


def test_unrepresentable_integer_is_unavailable(memory):
    assert predict(memory, {'load_ratio':10**1000})['signals']['load_ratio']['status'] == 'unavailable'


def test_history_window_excludes_old_rows_and_caps_support(memory):
    for _ in range(2): history(memory, {'battery_pct':100}, {'battery_pct':0})
    for _ in range(200): history(memory, {'battery_pct':50}, {'battery_pct':51}, 'reflect')
    signal = predict(memory)['signals']['battery_pct']
    assert signal['method'] == 'global_mean_delta' and signal['value'] == 51
    assert signal['evidence_count'] == 200 and signal['confidence'] == .95
    # Invalid recent rows consume the window; no unbounded search for valid evidence.
    for _ in range(200): history(memory, 'bad', 'bad')
    signal = predict(memory)['signals']['battery_pct']
    assert signal['method'] == 'persistence' and signal['evidence_count'] == 0


def test_inference_is_read_only_without_sensing_or_network(memory, monkeypatch):
    for _ in range(2): history(memory, CURRENT, CURRENT)
    before = list(memory.db.iterdump())
    def forbidden(*args, **kwargs): raise AssertionError('inference performed external IO')
    monkeypatch.setattr(socket, 'socket', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)
    monkeypatch.setattr('seed.body.Body.perceive', forbidden)
    allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION}
    memory.db.set_authorizer(lambda action,*args:sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY)
    try:
        first = predict(memory)
        assert predict(memory) == first
    finally:
        memory.db.set_authorizer(None)
    assert list(memory.db.iterdump()) == before


@pytest.mark.parametrize('before,after,current,expected', [
    (0,sys.float_info.max,0,sys.float_info.max),
    (sys.float_info.max,0,sys.float_info.max,0)])
def test_three_extreme_finite_deltas_do_not_overflow_mean(memory, before, after, current, expected):
    for _ in range(3):
        history(memory, {'load_ratio':before}, {'load_ratio':after})
    result = predict(memory, {'load_ratio':current})
    signal = result['signals']['load_ratio']
    assert signal['value'] == expected
    assert signal['evidence_count'] == 3
    json.dumps(result, allow_nan=False)


def test_batch_is_shared_math_with_source_clock_summary_and_no_reads(memory):
    from seed.predictor import Predictor
    from seed.learner import ACTIONS
    for action in ACTIONS:
        for _ in range(2): history(memory,CURRENT,{**CURRENT,'battery_pct':49},action)
    rows=[dict(r) for r in memory.db.execute('SELECT id,completed_at,action,state_before_json,state_after_json FROM transitions ORDER BY id DESC LIMIT 200')]
    predictor=Predictor(memory)
    expected={a:predictor.predict(CURRENT,a).to_dict() for a in ACTIONS}
    trace=[]
    memory.db.set_trace_callback(trace.append)
    batch=predictor.predict_candidates(CURRENT,ACTIONS,snapshot=rows)
    assert batch.predictions==expected
    assert batch.contributors['observe']['battery_pct']==dict(newest_source_transition_id=2,newest_source_completed_at=2.0,invalid_source_count=0)
    assert trace==[]
