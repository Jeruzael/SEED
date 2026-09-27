"""Literal B8 selection examples against real temporary SQLite evidence."""
import json
import math
import pytest
from seed.memory import Memory
from seed.learner import ACTIONS, Learner, state_key
from seed.predictor import Predictor
from seed.decision import DecisionSystem
from tests.test_predictor import history

STATE = dict(battery_pct=80, charging=False, load_ratio=.2, disk_free_pct=50, network=True, local_hour=12)

class RNG:
    def __init__(self, draw=.5, index=0):
        self.draw, self.index, self.calls = draw, index, []
    def random(self):
        self.calls.append('random')
        return self.draw
    def choice(self, pool):
        self.calls.append(tuple(pool))
        return pool[self.index]

@pytest.fixture
def system(home):
    memory = Memory(home / 'memory.sqlite3')
    result = DecisionSystem(memory, Predictor(memory), Learner(memory, epsilon=0), rng=RNG())
    yield result
    memory.close()

def choose(system, state=None):
    prepared = system.prepare(STATE if state is None else state, selected_at=100)
    assert not system.rng.calls
    return system.select(prepared)

def test_raw_q_fallback_and_random_tie_pool(system):
    system.memory.set_q(state_key(STATE), 'reflect', .7, 4)
    result = choose(system)
    assert result.decision.action == 'reflect'
    assert result.decision.score == .7
    assert result.record['selection_mode'] == 'fallback'
    assert result.record['choice_index'] is None
    assert system.rng.calls == ['random']
    assert result.record['candidates']['reflect']['components']['q_component'] == pytest.approx(.7058823529411764)

@pytest.mark.parametrize('index,expected', [(0,'observe'),(1,'rest')])
def test_low_disk_excludes_high_q_and_injected_tie_selects_either(system, index, expected):
    state = {**STATE, 'disk_free_pct':5}
    for action, q in [('consolidate',100),('observe',1),('rest',1)]:
        system.memory.set_q(state_key(state), action,q,0)
    system.rng.index = index
    result = choose(system,state)
    assert result.decision.action == expected
    assert result.record['selection_candidates'] == ['observe','rest']
    assert result.record['choice_index'] == index
    assert system.rng.calls == ['random',('observe','rest')]
    for action in ['reflect','consolidate']:
        assert result.record['candidates'][action]['constraint_reasons'] == ['low_disk']

@pytest.mark.parametrize('changes,reasons', [
    ({'battery_pct':10,'load_ratio':.9},['high_load','low_battery']),
    ({'battery_pct':20,'load_ratio':.8,'disk_free_pct':10},[]),
    ({'battery_pct':10,'charging':True},[]),
    ({'charging':None},['unknown_resources']),
])
def test_resource_boundaries(system,changes,reasons):
    result = choose(system,{**STATE,**changes})
    assert result.record['candidates']['reflect']['constraint_reasons'] == reasons

@pytest.mark.parametrize('change', [{'battery_pct':True},{'load_ratio':None},{'disk_free_pct':-1},{'local_hour':24},{'network':1}])
def test_invalid_current_state_aborts_before_rng(system,change):
    with pytest.raises(ValueError,match='invalid_state'):
        choose(system,{**STATE,**change})
    assert system.rng.calls == []

def test_forecast_conflict_literal_utilities(system):
    for action in ACTIONS:
        after = {**STATE, **({'battery_pct':0,'load_ratio':1,'disk_free_pct':0} if action=='reflect' else {})}
        for _ in range(20): history(system.memory,STATE,after,action)
        system.memory.set_q(state_key(STATE),action, 1 if action=='reflect' else 0 if action=='observe' else -1,0)
    result=choose(system)
    assert result.decision.action=='observe'
    assert result.record['policy_basis']=='composite'
    assert {a: c['decision_utility'] for a,c in result.record['candidates'].items()} == pytest.approx(
        dict(observe=.7425,reflect=.5175,consolidate=.6175,rest=.6175))

def test_partial_forecast_keeps_fixed_denominator(system):
    state={k:v for k,v in STATE.items() if k!='disk_free_pct'}
    for _ in range(20): history(system.memory,state,state)
    system.memory.set_q(state_key(state),'rest',-1,0)
    result=choose(system,state)
    c=result.record['candidates']['observe']
    assert c['components']['forecast_resource_risk']==pytest.approx(1/3)
    assert c['components']['model_uncertainty']==pytest.approx(11/30)
    assert c['decision_utility']==pytest.approx(.5783333333333334)
    assert c['resource_forecasts']['disk_free_pct']['value'] is None

@pytest.mark.parametrize('clock,status', [(100,'usable'),(400,'usable'),(400.001,'stale')])
def test_freshness_includes_300_second_boundary(system,clock,status):
    for _ in range(2): history(system.memory,STATE,STATE)
    system.memory.db.execute('UPDATE transitions SET completed_at=100')
    system.memory.db.commit()
    result=system.select(system.prepare(STATE,selected_at=clock))
    assert result.record['candidates']['observe']['resource_forecasts']['battery_pct']['status']==status

@pytest.mark.parametrize('value,visits', [('bad',0),(float('inf'),0),(1,-1),(1,9223372036854775807)])
def test_invalid_q_aborts_and_restores_connection(system,value,visits):
    system.memory.set_q(state_key(STATE),'observe',value,visits)
    before=system.memory.db.execute('PRAGMA busy_timeout').fetchone()[0]
    with pytest.raises(ValueError,match='invalid_q'):
        choose(system)
    assert not system.memory.db.in_transaction
    assert system.memory.db.execute('PRAGMA busy_timeout').fetchone()[0]==before
    assert system.rng.calls==[]

def test_oversized_history_falls_back_without_refill(system):
    history(system.memory, ' ' * 16385, '{}')
    result=choose(system)
    assert result.record['history']==dict(status='unavailable',reason='oversized_history',cutoff_transition_id=1,raw_rows_examined=1)
    assert result.record['fallback_reason']=='oversized_history'

def test_snapshot_uses_two_selects_and_predictor_batch_never_reads(system):
    for _ in range(2): history(system.memory,STATE,STATE)
    trace=[]
    system.memory.db.set_trace_callback(trace.append)
    prepared=system.prepare(STATE,selected_at=100)
    assert len([s for s in trace if s.lstrip().upper().startswith('SELECT')])==2
    assert any(s=='BEGIN' for s in trace)
    assert not system.memory.db.in_transaction
    trace.clear()
    system.select(prepared)
    assert not trace

@pytest.mark.parametrize('explore,index', [(0,0),(0,3),(1,0),(1,3)])
def test_composite_ties_use_injected_choice_even_epsilon_zero(system,explore,index):
    for _ in range(20): history(system.memory,STATE,STATE)
    system.learner.epsilon=explore
    system.rng.index=index
    result=choose(system)
    assert result.decision.action==ACTIONS[index]
    assert result.record['choice_index']==index
    assert system.rng.calls==['random',ACTIONS]

@pytest.mark.parametrize('clock,status,invalid', [('broken','invalid',2),(101,'invalid',0),(-1,'invalid',2)])
def test_bad_source_clocks_preserve_b2_values_but_do_not_supply_support(system,clock,status,invalid):
    for _ in range(2): history(system.memory,STATE,{**STATE,'battery_pct':75})
    system.memory.db.execute('UPDATE transitions SET completed_at=?',(clock,))
    system.memory.db.commit()
    result=choose(system)
    signal=result.record['candidates']['observe']['resource_forecasts']['battery_pct']
    assert signal['status']==status and signal['invalid_source_count']==invalid
    assert result.prediction['signals']['battery_pct']['value']==75
    assert result.record['policy_basis']=='legacy_q'

def test_writer_rejects_frozen_component_mutation(system):
    result=choose(system)
    result.record['candidates']['observe']['decision_utility']=.123
    with pytest.raises(ValueError): result.validate()

def test_frozen_prediction_digest_rejects_numeric_representation_change(system):
    result=choose(system)
    result.prediction['signals']['battery_pct']['value']=80
    with pytest.raises(ValueError): result.validate()

def test_history_read_error_is_auxiliary_but_q_failure_is_fatal(system):
    db=system.memory.db
    import sqlite3
    db.set_authorizer(lambda op,arg,*rest: sqlite3.SQLITE_DENY if op==sqlite3.SQLITE_READ and arg=='transitions' else sqlite3.SQLITE_OK)
    result=choose(system)
    assert result.record['fallback_reason']=='history_read_error'
    db.set_authorizer(None)
    system.rng.calls.clear()
    db.set_authorizer(lambda op,arg,*rest: sqlite3.SQLITE_DENY if op==sqlite3.SQLITE_READ and arg=='q_values' else sqlite3.SQLITE_OK)
    with pytest.raises(sqlite3.Error): choose(system)
    assert not db.in_transaction and system.rng.calls==[]
    db.set_authorizer(None)

def test_existing_transaction_is_not_rolled_back(system):
    system.memory.db.execute('BEGIN')
    with pytest.raises(ValueError,match='existing_transaction'): choose(system)
    assert system.memory.db.in_transaction
    system.memory.db.rollback()
