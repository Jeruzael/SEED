"""Literal statistical expectations and transactional evidence provenance."""
import json
import math
import sqlite3
import sys
import pytest
from seed.memory import Memory


def record(m, before=None, after=None, action='observe', eligible=True):
    return m.record_transition_experience(
        state_before=before or {}, action=action, state_after=after or {}, outcome={},
        legacy_reward=0, started_at=1, completed_at=2, world_model_eligible=eligible)[1]


def belief(m, signal='battery_pct', scope='global', value='', pending=False):
    table = 'world_pending' if pending else 'world_beliefs'
    row = m.db.execute(f'SELECT * FROM {table} WHERE signal=? AND scope=? AND scope_value=?',
                       (signal, scope, value)).fetchone()
    if not row:
        return None
    result = dict(row)
    result['value'] = json.loads(result.pop('value_json'))
    return result


@pytest.fixture
def model(home):
    from seed.world_model import WorldModel
    m = Memory(home/'memory.sqlite3')
    yield m, WorldModel(m)
    m.close()


def numeric(m, w, delta, signal='battery_pct', action='observe'):
    before = max(0, -delta)
    tid = record(m, {signal:before}, {signal:before+delta}, action)
    assert w.observe_transition(tid) is True
    return tid


def test_two_sample_threshold_is_durable_and_numeric_statistics(home):
    from seed.world_model import WorldModel
    m = Memory(home/'memory.sqlite3')
    first = record(m, {'battery_pct':80}, {'battery_pct':79})
    WorldModel(m).recover()
    assert belief(m) is None
    assert belief(m, pending=True)['evidence_count'] == 1
    assert not m.db.execute("SELECT 1 FROM events WHERE category='WORLD_MODEL'").fetchone()
    m.close()
    m = Memory(home/'memory.sqlite3')
    try:
        w = WorldModel(m)
        for before, after in [(79,78),(78,77)]:
            last = record(m, {'battery_pct':before}, {'battery_pct':after})
            w.recover()
        b = belief(m)
        assert b['value'] == dict(mean_delta=-1,mean_absolute_delta=1,min_delta=-1,max_delta=-1,
                                 confidence_kind='evidence_consistency')
        assert b['evidence_count'] == 3 and b['contradiction_count'] == 0
        assert b['confidence'] == .15
        assert (b['source_first_transition_id'],b['source_last_transition_id']) == (first,last)
        assert b['model_version'] == 1
        assert belief(m,pending=True) is None
        assert belief(m,scope='action',value='observe')['evidence_count'] == 3
    finally:
        m.close()


def test_incremental_mean_min_max_and_action_scopes(model):
    m,w = model
    for delta, action in [(1,'observe'),(3,'observe'),(-2,'reflect'),(-4,'reflect'),(0,'rest'),(8,'consolidate')]:
        numeric(m,w,delta,action=action)
    b = belief(m)
    assert b['value']['mean_delta'] == pytest.approx(1)
    assert b['value']['mean_absolute_delta'] == pytest.approx(3)
    assert b['value']['min_delta'] == -4 and b['value']['max_delta'] == 8
    assert b['evidence_count'] == 6
    assert belief(m,scope='action',value='observe')['value']['mean_delta'] == 2
    assert belief(m,scope='action',value='reflect')['value']['mean_delta'] == -3
    assert belief(m,scope='action',value='rest') is None


@pytest.mark.parametrize('sign', [1,-1])
@pytest.mark.parametrize('signal,eps', [('battery_pct',.05),('disk_free_pct',.01),('load_ratio',.02)])
def test_numeric_contradictions_preupdate_support_and_deadband(model,signal,eps,sign):
    m,w = model
    for _ in range(3): numeric(m,w,sign,signal)
    numeric(m,w,-sign,signal)  # existing n=3: not established yet
    assert belief(m,signal)['contradiction_count'] == 0
    numeric(m,w,-eps*sign,signal)  # boundary is neutral
    numeric(m,w,0,signal)
    assert belief(m,signal)['contradiction_count'] == 0
    numeric(m,w,-sign,signal)
    b = belief(m,signal)
    assert b['evidence_count'] == 7 and b['contradiction_count'] == 1
    assert b['value']['mean_delta'] == pytest.approx(sign*(1-eps)/7)
    assert b['confidence'] == pytest.approx(.35*6/7)


@pytest.mark.parametrize('samples,new,contradictions', [
    ([True]*4,False,1), ([False]*4,True,1),
    ([True,True,True,False],False,1), ([False,False,False,True],True,1),
    ([True,False,True,False],False,0), ([True]*3,False,0)])
def test_boolean_frequency_and_majority_thresholds(model,samples,new,contradictions):
    m,w = model
    for value in samples+[new]:
        w.observe_transition(record(m,after={'network':value}))
    b = belief(m,'network_reachable')
    assert b['value']['true_count'] == sum(samples)+new
    assert b['value']['false_count'] == len(samples)+1-sum(samples)-new
    assert b['value']['probability_true'] == (sum(samples)+new)/(len(samples)+1)
    assert b['evidence_count'] == len(samples)+1
    assert b['contradiction_count'] == contradictions


def test_confidence_rises_and_strong_belief_loses_confidence(model):
    from seed.world_model import confidence
    m,w = model
    assert confidence(0,0) == 0
    assert confidence(20,20) == 0
    for _ in range(2): numeric(m,w,1)
    low = belief(m)['confidence']
    for _ in range(18): numeric(m,w,1)
    strong = belief(m)['confidence']
    assert strong == .95 and strong > low
    numeric(m,w,-1)
    numeric(m,w,-1)
    b = belief(m)
    assert b['confidence'] == pytest.approx(.95*20/22)
    assert b['confidence'] < strong
    assert b['value']['mean_delta'] == pytest.approx(18/22)
    assert b['evidence_count'] == 22 and b['contradiction_count'] == 2


@pytest.mark.parametrize('bad', [None,True,False,'5',[],{},float('nan'),float('inf'),-1,101,10**400])
def test_invalid_numeric_is_skipped_but_other_signals_learn(model,bad):
    m,w = model
    for _ in range(2):
        tid=record(m, {'battery_pct':50,'disk_free_pct':50}, {'disk_free_pct':49,'network':True})
        # Simulate malformed/legacy persisted data which the normal writer rejects.
        m.db.execute('UPDATE transitions SET state_after_json=? WHERE id=?',
                     (json.dumps({'battery_pct':bad,'disk_free_pct':49,'network':True}),tid))
        m.db.commit()
        w.observe_transition(tid)
    assert belief(m) is None and belief(m,pending=True) is None
    assert belief(m,'disk_free_pct')['evidence_count'] == 2
    assert belief(m,'network_reachable')['evidence_count'] == 2


@pytest.mark.parametrize('raw', ['{broken','null','[]','"text"','['*1200+'0'+']'*1200])
def test_malformed_states_do_not_block_queue(model,raw):
    m,w=model
    tid=record(m)
    m.db.execute('UPDATE transitions SET state_before_json=?,state_after_json=? WHERE id=?',(raw,raw,tid))
    m.db.commit()
    assert w.recover() == 1
    assert m.db.execute('SELECT valid_signals FROM world_model_processed').fetchone()[0] == 0
    assert belief(m,pending=True) is None


@pytest.mark.parametrize('invalid', [None,0,1,'true',[],{}])
def test_network_requires_strict_bool_and_missing_numeric_is_unavailable(model,invalid):
    m,w=model
    for _ in range(2): w.observe_transition(record(m,after={'network':invalid}))
    assert m.db.execute('SELECT count(*) FROM world_beliefs').fetchone()[0] == 0
    assert m.db.execute('SELECT count(*) FROM world_pending').fetchone()[0] == 0


def test_load_extreme_finite_values_do_not_overflow_incremental_mean(model):
    m,w=model
    maximum=sys.float_info.max
    for delta in [maximum,-maximum,maximum,-maximum]: numeric(m,w,delta,'load_ratio')
    b=belief(m,'load_ratio')
    assert abs(b['value']['mean_delta']) <= maximum*1e-15
    assert b['value']['mean_absolute_delta'] == maximum
    assert all(math.isfinite(v) for k,v in b['value'].items() if k!='confidence_kind')


def test_idempotency_even_for_contradiction(model):
    m,w=model
    for _ in range(4): numeric(m,w,1)
    tid=numeric(m,w,-1)
    before=list(m.db.iterdump())
    assert w.observe_transition(tid) is False
    assert list(m.db.iterdump()) == before
    assert belief(m)['evidence_count'] == 5 and belief(m)['contradiction_count'] == 1
    assert m.db.execute('SELECT count(*) FROM world_model_processed WHERE transition_id=?',(tid,)).fetchone()[0] == 1


def test_failure_rolls_back_beliefs_pending_events_marker_and_retries_once(model):
    m,w=model
    numeric(m,w,1)
    tid=record(m,{'battery_pct':50},{'battery_pct':49,'network':True})
    source=tuple(m.db.execute('SELECT * FROM transitions WHERE id=?',(tid,)).fetchone())
    m.db.execute("""CREATE TRIGGER fail_marker BEFORE INSERT ON world_model_processed
                    BEGIN SELECT RAISE(ABORT,'model failed'); END""")
    before=list(m.db.iterdump())
    with pytest.raises(sqlite3.IntegrityError,match='model failed'): w.observe_transition(tid)
    assert list(m.db.iterdump()) == before
    assert tuple(m.db.execute('SELECT * FROM transitions WHERE id=?',(tid,)).fetchone()) == source
    m.db.execute('DROP TRIGGER fail_marker')
    assert w.recover() == 1
    assert w.recover() == 0
    assert belief(m)['evidence_count'] == 2
    assert belief(m,'network_reachable',pending=True)['evidence_count'] == 1


def test_no_historical_backfill_and_ordered_bounded_recovery(model):
    m,w=model
    old=[record(m,{'battery_pct':80},{'battery_pct':79},eligible=False) for _ in range(105)]
    assert w.recover() == 0 and w.observe_transition(old[0]) is False
    new=[record(m,{'battery_pct':80},{'battery_pct':79}) for _ in range(103)]
    with pytest.raises(ValueError,match='order'): w.observe_transition(new[-1])
    sql=[]
    m.db.set_trace_callback(sql.append)
    assert w.recover() == 100
    m.db.set_trace_callback(None)
    assert belief(m)['evidence_count'] == 100
    assert m.db.execute('SELECT count(*) FROM world_model_queue').fetchone()[0] == 3
    assert w.recover() == 3
    assert belief(m)['evidence_count'] == 103
    source_reads=[s for s in sql if 'FROM transitions' in s]
    assert len(source_reads) == 100
    assert all('WHERE id=' in s for s in source_reads)
    assert any('FROM world_model_queue ORDER BY transition_id LIMIT 100' in s for s in sql)
    assert m.db.execute('SELECT count(*) FROM world_model_processed').fetchone()[0] == 103


def test_events_only_promotion_material_revision_or_contradiction(model):
    m,w=model
    for _ in range(20): numeric(m,w,1)
    before=m.db.execute("SELECT count(*) FROM events WHERE category='WORLD_MODEL'").fetchone()[0]
    assert before == 36  # n=2..19, two scopes; n=20 same stats/confidence
    numeric(m,w,1)
    assert m.db.execute("SELECT count(*) FROM events WHERE category='WORLD_MODEL'").fetchone()[0] == before
    tid=numeric(m,w,-1)
    events=[json.loads(r[0]) for r in m.db.execute("SELECT data_json FROM events WHERE category='WORLD_MODEL' ORDER BY id DESC LIMIT 2")]
    assert len(events)==2
    for event in events:
        assert event['transition_id']==tid and event['change']=='contradicted'
        assert event['old_confidence']==.95 and event['new_confidence']<.95
        assert event['evidence_count']==22 and event['contradiction_count']==1


def test_unknown_actions_not_autonomous_evidence(model):
    m,w=model
    for _ in range(2): w.observe_transition(record(m,after={'network':True},action='owner_note'))
    assert m.db.execute('SELECT count(*) FROM world_pending').fetchone()[0]==0
