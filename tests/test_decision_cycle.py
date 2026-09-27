import json
import sqlite3
import pytest
from seed.organism import SeedOrganism
from tests.test_decision import STATE, RNG
from seed.learner import state_key

@pytest.fixture
def core(home,monkeypatch):
    monkeypatch.setattr('seed.body.Body.perceive',lambda _:dict(STATE))
    monkeypatch.setattr('seed.organism.time.time',lambda:100.)
    monkeypatch.setattr('seed.organism.time.monotonic',lambda:10.)
    c=SeedOrganism(home)
    c.learner.epsilon=0
    c.decisions.rng=RNG()
    yield c
    c.close()

def assert_no_completion(c):
    for table in ('q_values','transitions','decision_records','world_model_queue','curiosity_assessments','self_model_current'):
        assert c.memory.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]==0
    assert c.memory.db.execute("SELECT count(*) FROM events WHERE category IN ('ERROR','LEARNING','CURIOSITY','PREDICTION_ERROR','SELF_MODEL')").fetchone()[0]==0

@pytest.mark.parametrize('elapsed,status',[(5.,'completed'),(5.001,'skipped')])
def test_stale_boundary_skips_without_learning_or_second_perception(core,monkeypatch,elapsed,status):
    now=[10.]
    calls=[]
    monkeypatch.setattr('seed.organism.time.monotonic',lambda:now[0])
    monkeypatch.setattr(core.body,'perceive',lambda: calls.append(1) or dict(STATE))
    prepare=core.decisions.prepare
    def delayed(*a,**kw):
        result=prepare(*a,**kw)
        now[0]+=elapsed
        return result
    monkeypatch.setattr(core.decisions,'prepare',delayed)
    result=core.cycle()
    assert result.status==status and result.delay_seconds==8
    if status=='skipped':
        assert result.reason=='stale_decision' and len(calls)==1
        assert core.decisions.rng.calls==[]
        assert_no_completion(core)
        runtime=json.loads(core.memory.db.execute('SELECT data_json FROM runtime').fetchone()[0])
        assert runtime['current_action'] is None and runtime['action_started_at'] is None
        assert runtime['activity']=='idle' and runtime['next_observation_at']==108
    else:
        assert len(calls)==2
        assert core.memory.db.execute('SELECT count(*) FROM decision_records').fetchone()[0]==1

def test_late_stale_diagnostic_correlates_attempt_and_never_dispatches(core,monkeypatch):
    now=[10.]
    monkeypatch.setattr('seed.organism.time.monotonic',lambda:now[0])
    emit=core.telemetry.emit
    def slow(category,source,message,data):
        emit(category,source,message,data)
        if category=='ACTION': now[0]=16.
    monkeypatch.setattr(core.telemetry,'emit',slow)
    monkeypatch.setattr(core,'perform_action',lambda *a,**kw:pytest.fail('stale dispatch'))
    monkeypatch.setattr(core.learner,'reward',lambda *a:pytest.fail('stale reward'))
    result=core.cycle()
    assert result.status=='skipped'
    assert_no_completion(core)
    events=[json.loads(r[0]) for r in core.memory.db.execute("SELECT data_json FROM events WHERE category='DECISION' ORDER BY id")]
    assert len(events)==2 and events[0]['decision_id']==events[1]['decision_id']
    assert events[1]['phase']=='before_dispatch' and len(json.dumps(events[1]).encode())<=512

@pytest.mark.parametrize('phase',['before','after_prepare','before_dispatch'])
def test_owner_stop_precedes_selection_and_dispatch(core,monkeypatch,phase):
    if phase=='before': core.stop()
    elif phase=='after_prepare':
        original=core.decisions.prepare
        def prepare(*a,**kw):
            result=original(*a,**kw);core.stop();return result
        monkeypatch.setattr(core.decisions,'prepare',prepare)
    else:
        original=core.telemetry.emit
        def emit(*args):
            original(*args)
            if args[0]=='ACTION':core.stop()
        monkeypatch.setattr(core.telemetry,'emit',emit)
    monkeypatch.setattr(core,'perform_action',lambda *a,**kw:pytest.fail('stopped dispatch'))
    result=core.cycle()
    assert (result.status,result.delay_seconds,result.reason)==('stopped',None,'owner_stop')
    assert_no_completion(core)


def test_completed_payload_digest_and_legacy_q_update(core):
    core.memory.set_q(state_key(STATE),'reflect',.7,4)
    result=core.cycle()
    assert result.status=='completed' and result.delay_seconds==12 and result.reason is None
    assert core.memory.get_q(state_key(STATE),'reflect')==pytest.approx((.655,5))
    record=json.loads(core.memory.db.execute('SELECT data_json FROM decision_records').fetchone()[0])
    prediction=json.loads(core.memory.db.execute('SELECT prediction_json FROM transitions').fetchone()[0])
    from seed.decision_record import prediction_digest
    assert record['selected_prediction_sha256']==prediction_digest(prediction)
    assert record['candidates']['reflect']['q_value']==.7


def test_stale_retry_waits_full_interval_and_stop_interrupts(core,monkeypatch):
    now=[10.]; attempts=[]; waits=[]
    monkeypatch.setattr('seed.organism.time.monotonic',lambda:now[0])
    monkeypatch.setattr(core,'awaken',lambda:None)
    prepare=core.decisions.prepare
    def slow(*a,**kw):
        attempts.append(now[0]);result=prepare(*a,**kw);now[0]+=6;return result
    monkeypatch.setattr(core.decisions,'prepare',slow)
    def wait(seconds):
        waits.append(seconds);now[0]+=seconds
        if len(attempts)==2:core.stop()
    monkeypatch.setattr(core.stop_event,'wait',wait)
    core.run()
    assert attempts==[10.,24.] and waits==[2.,2.,2.,2.,2.]
    with sqlite3.connect(core.home/'memory.sqlite3') as db:
        assert db.execute('SELECT count(*) FROM decision_records').fetchone()[0]==0
        assert db.execute("SELECT count(*) FROM events WHERE category='ERROR'").fetchone()[0]==0
