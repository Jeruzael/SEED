import json
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor
import pytest
from seed.memory import Memory
from tests.test_curiosity_migrations import assessment


def store(m,**changes):
    payload=assessment()
    payload.update(changes)
    return m.record_transition_experience(state_before={},state_after={},action='observe',outcome={},
        legacy_reward=0,started_at=1,completed_at=2,curiosity=payload)[1]


def row(m,tid): return dict(m.db.execute('SELECT * FROM curiosity_assessments WHERE transition_id=?',(tid,)).fetchone())


@pytest.fixture
def setup(home):
    from seed.curiosity_attention import CuriosityAttention
    m=Memory(home/'memory.sqlite3')
    now=[1000.]
    yield m,CuriosityAttention(m,clock=lambda:now[0]),now
    m.close()


def test_claim_is_durable_before_callback_and_at_most_once(setup):
    m,attention,now=setup
    tid=store(m)
    calls=[]
    def reflect():
        assert not m.db.in_transaction
        r=row(m,tid)
        assert r['reflection_claimed']==1 and r['reflection_completed']==0
        assert m.db.execute('SELECT last_reflection_at FROM curiosity_runtime').fetchone()[0]==1000
        calls.append(1)
    assert attention.execute(tid,reflect) is True
    assert attention.execute(tid,reflect) is False
    assert calls==[1]
    r=row(m,tid)
    assert r['reflection_completed']==1 and r['claimed_at']==r['completed_at']==1000
    assert r['score']==.8 and r['failure_reason'] is None


@pytest.mark.parametrize('distance,elapsed,reason',[(9,300,'cooldown_transitions'),(10,299,'cooldown_time'),
                                                  (10,-1,'cooldown_time'),(10,300,None)])
def test_both_cooldown_conditions_required(setup,distance,elapsed,reason):
    m,attention,now=setup
    first=store(m)
    assert attention.execute(first,lambda:None)
    for _ in range(distance): last=store(m)
    now[0]+=elapsed
    calls=[]
    assert attention.execute(last,lambda:calls.append(1)) is (reason is None)
    assert len(calls)==(reason is None)
    assert row(m,last)['suppression_reason']==reason
    assert row(m,last)['score']==.8
    if reason:
        now[0]+=1000
        assert not attention.execute(last,lambda:calls.append(1))  # terminal suppression


def test_transition_id_gaps_and_owner_episodes_do_not_bypass_budget(setup):
    m,attention,now=setup
    first=store(m)
    attention.execute(first,lambda:None)
    for _ in range(20): m.episode('experience',{},action='observe',note='source=owner_command')
    m.db.execute("UPDATE sqlite_sequence SET seq=100 WHERE name='transitions'")
    m.db.commit()
    last=store(m)
    assert last==101
    now[0]+=300
    assert not attention.execute(last,lambda:pytest.fail('No transition budget'))
    assert row(m,last)['suppression_reason']=='cooldown_transitions'


def test_restart_retains_cooldown_and_claimed_but_unfinished_work_is_lost(home):
    from seed.curiosity_attention import CuriosityAttention
    m=Memory(home/'memory.sqlite3')
    first=store(m)
    assert CuriosityAttention(m,clock=lambda:1000).claim(first)
    m.close()
    m=Memory(home/'memory.sqlite3')
    try:
        attention=CuriosityAttention(m,clock=lambda:1400)
        assert not attention.execute(first,lambda:pytest.fail('Claim cannot be replayed'))
        second=store(m)
        assert not attention.execute(second,lambda:pytest.fail('Restart cannot reset cooldown'))
        assert row(m,first)['reflection_claimed']==1 and row(m,first)['reflection_completed']==0
        assert row(m,second)['suppression_reason']=='cooldown_transitions'
    finally:m.close()


def test_two_connections_cannot_both_claim_same_transition(home):
    from seed.curiosity_attention import CuriosityAttention
    a,b=Memory(home/'memory.sqlite3'),Memory(home/'memory.sqlite3')
    try:
        tid=store(a)
        workers=[CuriosityAttention(m,clock=lambda:1000) for m in (a,b)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            result=list(pool.map(lambda w:w.claim(tid),workers))
        assert sorted(result)==[False,True]
        assert a.db.execute('SELECT count(*) FROM curiosity_runtime').fetchone()[0]==1
    finally:a.close();b.close()


def test_claim_event_failure_rolls_back_claim_and_cooldown(setup):
    m,attention,now=setup
    tid=store(m)
    m.db.execute("""CREATE TRIGGER fail_claim BEFORE INSERT ON events WHEN NEW.category='CURIOSITY'
                     BEGIN SELECT RAISE(ABORT,'event failed'); END""")
    with pytest.raises(sqlite3.IntegrityError,match='event failed'): attention.claim(tid)
    assert row(m,tid)['reflection_claimed']==0
    assert m.db.execute('SELECT count(*) FROM curiosity_runtime').fetchone()[0]==0


def test_optional_failure_is_recorded_and_consumes_budget(setup):
    m,attention,now=setup
    tid=store(m)
    def fail(): raise RuntimeError('auxiliary failed')
    assert attention.execute(tid,fail) is False
    r=row(m,tid)
    assert r['reflection_claimed']==1 and r['reflection_completed']==0
    assert r['failure_reason']=='RuntimeError: auxiliary failed' and r['score']==.8
    events=[json.loads(r[0]) for r in m.db.execute("SELECT data_json FROM events WHERE category='CURIOSITY'")]
    assert [e['attention_outcome'] for e in events]==['claimed','failed']
    assert not attention.execute(tid,lambda:pytest.fail('Failed work cannot repeat'))


def test_serious_storage_error_propagates_without_releasing_claim(setup):
    m,attention,now=setup
    tid=store(m)
    def fail(): raise sqlite3.DatabaseError('database corrupted')
    with pytest.raises(sqlite3.DatabaseError): attention.execute(tid,fail)
    assert row(m,tid)['reflection_claimed']==1


def test_owner_stop_prevents_claim_and_reflection(setup):
    m,attention,now=setup
    stop=threading.Event()
    stop.set()
    tid=store(m)
    assert not attention.execute(tid,lambda:pytest.fail('Owner stopped'),stop)
    assert row(m,tid)['suppression_reason']=='owner_stop' and row(m,tid)['reflection_claimed']==0


def test_owner_stop_after_claim_prevents_execution(setup,monkeypatch):
    m,attention,now=setup
    tid=store(m)
    stop=threading.Event()
    claim=attention.claim
    def claim_then_stop(*args):
        result=claim(*args)
        stop.set()
        return result
    monkeypatch.setattr(attention,'claim',claim_then_stop)
    assert not attention.execute(tid,lambda:pytest.fail('Stopped after claim'),stop)
    assert row(m,tid)['reflection_claimed']==1 and row(m,tid)['reflection_completed']==0
    assert row(m,tid)['suppression_reason']=='owner_stop'


def test_claim_rechecks_coverage_not_only_cached_eligibility(setup):
    m,attention,now=setup
    tid=store(m,coverage=.49)
    assert not attention.execute(tid,lambda:pytest.fail('Sparse evidence'))
    assert row(m,tid)['suppression_reason']=='insufficient_coverage'


def test_cooldown_queries_are_bounded(setup):
    m,attention,now=setup
    tid=store(m)
    attention.execute(tid,lambda:None)
    for _ in range(12): last=store(m)
    now[0]+=300
    sql=[]
    m.db.set_trace_callback(sql.append)
    attention.execute(last,lambda:None)
    m.db.set_trace_callback(None)
    counts=[s for s in sql if 'FROM transitions' in s and 'id >' in s]
    assert len(counts)==1 and 'LIMIT 10' in counts[0]
