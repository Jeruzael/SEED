"""Literal measurements, bounded reads, durable publication and failure isolation."""
import copy
import json
import sqlite3
from threading import Event
import pytest
from seed.memory import Memory
from seed.telemetry import Telemetry
from seed.prediction_error import evaluate_prediction
from tests.test_prediction_error import payload,predicted

STATE=dict(battery_pct=80,charging=True,load_ratio=.2,load_5m_ratio=.3,
           disk_free_pct=70,network=False,hostname='synthetic',machine='synthetic',macos='synthetic',wall_time=1000)


def record(m,state=None,evaluation=None,at=1001,action='observe'):
    return m.record_transition_experience(state_before=STATE,state_after=STATE if state is None else state,
        action=action,outcome={},legacy_reward=.45,started_at=at-1,completed_at=at,
        prediction_error=evaluation)[1]


def current(m):
    row=m.db.execute('SELECT data_json FROM self_model_current').fetchone()
    return json.loads(row[0]) if row else None


def update(m,tid,at=1002,stop=None):
    from seed.self_model import SelfModel
    return SelfModel(m,clock=lambda:at).update(tid,'synthetic',stop or Event())


@pytest.fixture
def memory(home):
    m=Memory(home/'memory.sqlite3')
    yield m
    m.close()


def test_available_observations_are_recorded_facts_and_reopen_survives(memory):
    tid=record(memory)
    assert update(memory,tid)=='updated'
    p=current(memory)
    assert p['observations']['network']['value'] is False
    assert p['observations']['network']['status']=='available'
    assert p['source_transition_id']==tid and p['sources']['observation']['source_observed_at']==1000
    assert p['prediction_performance']['score']['status']=='insufficient_evidence'
    assert p['memory']['storage']['value']['transition_count']=={'count':1,'relation':'exact'}
    assert p['memory']['storage']['value']['logical_allocated_bytes']==p['memory']['storage']['value']['page_count']*p['memory']['storage']['value']['page_size']
    assert p['capabilities']['unsupported']['arbitrary_tools']['status']=='not_supported'
    assert p['capabilities']['actions']['consolidate']['value']['selectable'] is True
    with sqlite3.connect(memory.path) as db:
        assert json.loads(db.execute('SELECT data_json FROM self_model_current').fetchone()[0])==p
    events=[json.loads(r[0]) for r in memory.db.execute("SELECT data_json FROM events WHERE category='SELF_MODEL'")]
    assert len(events)==1 and events[0]['status']=='updated' and events[0]['source_transition_id']==tid
    assert p['source_event_id']==0


@pytest.mark.parametrize('key,value,status',[
    ('battery_pct',None,'unavailable'),('charging',None,'unavailable'),('charging',False,'available'),
    ('charging',1,'error'),('load_ratio',True,'error'),('load_ratio',-1,'error'),
    ('battery_pct',101,'error'),('disk_free_pct','70','error'),('network',None,'unavailable'),
    ('network',False,'available'),('hostname','','unavailable'),('machine','x'*129,'error')])
def test_sensor_domain_and_absence_are_not_healthy_defaults(memory,key,value,status):
    tid=record(memory,{**STATE,key:value})
    assert update(memory,tid)=='updated'
    f=current(memory)['observations'][key]
    assert f['status']==status
    assert f['value']==(value if status=='available' else None)


@pytest.mark.parametrize('raw',['{broken','[]','{"wall_time":NaN}','{"wall_time":1000,"network":true,"network":false}','['*20+']'*20,' '*17000])
def test_bad_current_json_is_explicit_error_without_discarding_storage_facts(memory,raw):
    tid=record(memory)
    with memory.db:memory.db.execute('UPDATE transitions SET state_after_json=? WHERE id=?',(raw,tid))
    assert update(memory,tid)=='updated'
    p=current(memory)
    assert all(f['status']=='error' for f in p['observations'].values())
    assert p['memory']['storage']['status']=='available'


@pytest.mark.parametrize('wall,expected',[(None,'unavailable'),(940,'stale'),(1003,'error'),('1000','error')])
def test_observation_clock_is_not_replaced_by_builder_time(memory,wall,expected):
    tid=record(memory,{**STATE,'wall_time':wall})
    assert update(memory,tid)=='updated'
    assert current(memory)['observations']['network']['status']==expected


def test_read_projection_ttl_boundary_and_clock_reversal_never_writes(memory):
    from seed.self_model import project_snapshot
    tid=record(memory);update(memory,tid)
    p=current(memory);saved=copy.deepcopy(p)
    assert project_snapshot(p,1060)['observations']['network']['status']=='available'
    assert project_snapshot(p,1061)['observations']['network']['status']=='stale'
    assert project_snapshot(p,999)['observations']['network']['status']=='error'
    assert p==saved==current(memory)


def test_retrospective_literal_denominators_and_raw_window(memory):
    forecast=payload({'battery_pct':predicted(73),'load_ratio':predicted(.4),
                      'disk_free_pct':predicted(49),'network_reachable':predicted(True,probability_true=.5)})
    for actual in ({'battery_pct':71,'load_ratio':.6,'disk_free_pct':48,'network':False},{'battery_pct':73},{}):
        tid=record(memory,evaluation=evaluate_prediction(forecast,actual).to_dict())
    update(memory,tid)
    p=current(memory)['prediction_performance']
    assert p['coverage']['value']=={'samples':3,'mean':pytest.approx(5/12)}
    assert p['score']['value']=={'samples':2,'mean_normalized_error':pytest.approx(.06),'accuracy_score':pytest.approx(.94)}
    for _ in range(100):tid=record(memory)
    with memory.db:memory.db.execute("UPDATE transitions SET prediction_error_json='{broken' WHERE id=?",(tid,))
    update(memory,tid)
    p=current(memory)['prediction_performance']
    assert p['window']['value']['raw_rows']==100
    assert p['window']['value']['invalid_evaluations']==1
    assert p['window']['value']['missing_evaluations']==99
    assert p['score']['status']=='error' and p['score']['value']['samples']==0


def test_future_row_excluded_and_corrupt_aggregate_not_trusted(memory):
    e=evaluate_prediction(payload({'battery_pct':predicted(80)}),STATE).to_dict()
    tid=record(memory,evaluation=e)
    record(memory,evaluation=e,at=2000)
    assert update(memory,tid)=='updated'
    assert current(memory)['prediction_performance']['window']['value']['raw_transition_ids']==[tid]
    e['aggregate']['accuracy_score']=.2
    last=record(memory,evaluation=e)
    update(memory,last)
    p=current(memory)['prediction_performance']
    assert p['window']['value']['invalid_evaluations']==2
    assert p['score']['reason']=='partial_window' and p['score']['value']['samples']==1


@pytest.mark.parametrize('n,count,relation',[(999,999,'exact'),(1000,1000,'exact'),(1001,1001,'at_least'),(1002,1001,'at_least')])
def test_counts_saturate_without_claiming_lifetime_totals(memory,n,count,relation):
    for _ in range(n):tid=record(memory)
    assert update(memory,tid)=='updated'
    assert current(memory)['memory']['storage']['value']['transition_count']=={'count':count,'relation':relation}


def test_error_sample_and_runtime_provenance(memory):
    t=Telemetry(memory)
    t.runtime(heartbeat=980,last_successful_cycle=970,session_id='old')
    for i in range(105):
        with memory.db:memory.db.execute("INSERT INTO events(ts,category,source,message,data_json) VALUES(990,'ERROR','synthetic','private','{}')")
    tid=record(memory);assert update(memory,tid)=='updated'
    p=current(memory)
    assert p['recent_failures']['value']['count']==100
    assert p['recent_failures']['value']['has_older_retained_errors'] is True
    assert p['recent_failures']['value']['latest_valid_event']['id']==105
    assert p['memory']['runtime_reported']['status']=='stale'
    assert p['memory']['runtime_reported']['value']['last_successful_cycle']==970
    assert p['source_event_id']==105
    assert 'private' not in json.dumps(p)


def test_snapshot_and_event_are_atomic_on_insert_failure(memory):
    first=record(memory);update(memory,first);saved=current(memory)
    tid=record(memory)
    memory.db.execute("CREATE TRIGGER fail_summary BEFORE INSERT ON events WHEN NEW.category='SELF_MODEL' BEGIN SELECT RAISE(ABORT,'blocked'); END")
    assert update(memory,tid)=='failed'
    assert current(memory)==saved
    assert memory.db.execute('SELECT count(*) FROM transitions').fetchone()[0]==2
    assert memory.db.execute('PRAGMA busy_timeout').fetchone()[0]==2000
    assert not memory.db.in_transaction


def test_stop_duplicate_and_caller_transaction_are_preserved(memory):
    tid=record(memory);stop=Event();stop.set()
    assert update(memory,tid,stop=stop)=='skipped' and current(memory) is None
    assert update(memory,tid)=='updated'
    before=list(memory.db.iterdump())
    assert update(memory,tid)=='skipped' and list(memory.db.iterdump())==before
    memory.db.execute("INSERT INTO meta VALUES('uncommitted','1')")
    assert update(memory,tid)=='skipped' and memory.db.in_transaction
    assert memory.db.execute("SELECT value FROM meta WHERE key='uncommitted'").fetchone()[0]=='1'
    memory.db.rollback()


def test_read_budget_and_no_io_other_than_database(memory,monkeypatch):
    import socket
    def forbidden(*a,**kw):raise AssertionError('new sensing/network')
    monkeypatch.setattr('seed.body.Body.perceive',forbidden)
    monkeypatch.setattr(socket,'socket',forbidden)
    tid=record(memory);sql=[];memory.db.set_trace_callback(sql.append)
    assert update(memory,tid)=='updated'
    memory.db.set_trace_callback(None)
    reads=[q for q in sql if q.lstrip().upper().startswith('SELECT') or q in ('PRAGMA page_size','PRAGMA page_count','PRAGMA busy_timeout')]
    assert len(reads)<=15
    assert not any('COUNT(' in q.upper() for q in reads)
    assert len(json.dumps(current(memory)).encode())<=32768


def test_strict_snapshot_validation_rejects_nested_corruption(memory):
    from seed.self_model import validate_snapshot,decode_snapshot
    tid=record(memory);update(memory,tid);p=current(memory)
    validate_snapshot(p)
    for change in ('sensor','source','score','capability','extra'):
        bad=copy.deepcopy(p)
        if change=='sensor':bad['observations']['battery_pct']['value']=999
        if change=='source':bad['observations']['battery_pct']['source']='unknown'
        if change=='score':bad['prediction_performance']['score']['value']['accuracy_score']=1
        if change=='capability':bad['capabilities']['unsupported']['arbitrary_tools']['value']=True
        if change=='extra':bad['extra']='unrecognized'
        with pytest.raises(ValueError):validate_snapshot(bad)
    for raw in (' '*32769,'{"model":"a","model":"b"}','{"value":Infinity}'):
        with pytest.raises(ValueError):decode_snapshot(raw)


def test_suppressed_audit_is_separate_from_selectability_and_has_recorded_reason(memory):
    from seed.semantic_memory import Consolidator
    Consolidator(memory,clock=lambda:999).run({'disk_free_pct':5},'owner_requested')
    tid=record(memory);assert update(memory,tid)=='updated'
    p=current(memory)
    assert p['capabilities']['actions']['consolidate']['value']['selectable'] is True
    audit=p['memory']['latest_consolidation']['value']
    assert audit['status']=='suppressed' and audit['source_beliefs_examined']==0
    assert audit['suppression_reason']=='low_disk' and audit['provenance']=='owner_requested'
    assert 'transition_id' not in audit
    with memory.db:memory.db.execute("UPDATE consolidation_runs SET result_json=?",(' '*17000,))
    tid=record(memory);assert update(memory,tid)=='updated'
    audit=current(memory)['memory']['latest_consolidation']
    assert audit['status']=='error' and audit['reason']=='oversized_source'
    assert audit['value']['status']=='suppressed' and audit['value']['suppression_reason'] is None


@pytest.mark.parametrize('change',['supported_bool','action_bool','future_success','bad_reason'])
def test_observer_cannot_accept_structurally_plausible_false_measurements(memory,change):
    from seed.self_model import validate_snapshot
    Telemetry(memory).runtime(heartbeat=1000,last_successful_cycle=999,session_id='synthetic')
    tid=record(memory);update(memory,tid);p=current(memory)
    if change=='supported_bool':p['capabilities']['sensors']['network']['supported']=1
    if change=='action_bool':p['capabilities']['actions']['reflect']['value']['implemented']=1
    if change=='future_success':p['memory']['runtime_reported']['value']['last_successful_cycle']=2000
    if change=='bad_reason':p['observations']['battery_pct'].update(status='error',reason='no_scored_evaluations')
    with pytest.raises(ValueError):validate_snapshot(p)


def test_progress_abort_removes_handler_and_restores_timeout(memory,monkeypatch):
    import seed.self_model as module
    tid=record(memory)
    def expensive(db,tid):
        db.execute('WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n WHERE x<1000000) SELECT sum(x) FROM n').fetchone()
        raise AssertionError('query should be interrupted')
    monkeypatch.setattr(module,'_read_evidence',expensive)
    assert update(memory,tid)=='failed' and current(memory) is None
    assert memory.db.execute('PRAGMA busy_timeout').fetchone()[0]==2000
    assert memory.db.execute('WITH RECURSIVE n(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM n WHERE x<10000) SELECT sum(x) FROM n').fetchone()[0]==50005000
    assert not memory.db.in_transaction


def test_writer_contention_is_optional_and_does_not_replace_previous_row(memory):
    tid=record(memory);update(memory,tid);saved=current(memory)
    tid=record(memory)
    other=sqlite3.connect(memory.path)
    try:
        other.execute('BEGIN IMMEDIATE')
        assert update(memory,tid)=='failed'
        assert current(memory)==saved
    finally:other.rollback();other.close()
    assert update(memory,tid)=='updated'


def test_retention_boundary_rolls_back_with_snapshot_write(memory):
    # B7's event is ID50100, where the existing emit helper deletes <=100.
    with memory.db:
        memory.db.execute("INSERT INTO events VALUES(1,1,'ERROR','synthetic','retained','{}')")
        memory.db.execute("INSERT INTO events VALUES(50099,1,'SYSTEM','synthetic','last','{}')")
        memory.db.execute("CREATE TRIGGER fail_cleanup BEFORE DELETE ON events BEGIN SELECT RAISE(ABORT,'retention failed'); END")
    tid=record(memory)
    assert update(memory,tid)=='failed' and current(memory) is None
    assert memory.db.execute('SELECT id FROM events ORDER BY id').fetchall()[0][0]==1
    memory.db.execute('DROP TRIGGER fail_cleanup')
    assert update(memory,tid)=='updated'
    assert memory.db.execute('SELECT 1 FROM events WHERE id=1').fetchone() is None
    assert current(memory)['recent_failures']['value']['latest_valid_event']['id']==1


def test_stop_during_build_discards_optional_publication(memory,monkeypatch):
    import seed.self_model as module
    stop=Event();build=module.build_snapshot
    def stop_build(*args):
        p=build(*args);stop.set();return p
    monkeypatch.setattr(module,'build_snapshot',stop_build)
    tid=record(memory)
    assert update(memory,tid,stop=stop)=='skipped'
    assert current(memory) is None and not memory.db.in_transaction
    assert not memory.db.execute("SELECT 1 FROM events WHERE category='SELF_MODEL'").fetchone()


def test_interrupt_does_not_get_swallowed_or_leave_transaction(memory,monkeypatch):
    import seed.self_model as module
    def interrupt(*args):raise KeyboardInterrupt()
    monkeypatch.setattr(module,'build_snapshot',interrupt)
    tid=record(memory)
    with pytest.raises(KeyboardInterrupt):update(memory,tid)
    assert not memory.db.in_transaction and current(memory) is None
    assert memory.db.execute('PRAGMA busy_timeout').fetchone()[0]==2000


@pytest.mark.parametrize('raw,missing,unsupported,invalid',[
    (None,1,0,0),('{bad',0,0,1),(' '*17000,0,0,1),
    (json.dumps(dict(evaluator='future',evaluator_version=2,prediction_model='future',prediction_model_version=2,horizon='future')),0,1,0)])
def test_evaluation_absence_and_unsupported_contract_are_distinct(memory,raw,missing,unsupported,invalid):
    tid=record(memory)
    with memory.db:memory.db.execute('UPDATE transitions SET prediction_error_json=? WHERE id=?',(raw,tid))
    assert update(memory,tid)=='updated'
    w=current(memory)['prediction_performance']['window']['value']
    assert (w['missing_evaluations'],w['unsupported_evaluations'],w['invalid_evaluations'])==(missing,unsupported,invalid)


def test_independent_prediction_clocks_and_zero_coverage(memory):
    from seed.self_model import project_snapshot
    good=evaluate_prediction(payload({'battery_pct':predicted(80)}),STATE).to_dict()
    empty=evaluate_prediction(payload({}),{}).to_dict()
    record(memory,evaluation=good,at=800)
    tid=record(memory,evaluation=empty,at=1001)
    assert update(memory,tid)=='updated'
    p=project_snapshot(current(memory),1101)
    assert p['prediction_performance']['score']['status']=='stale'
    assert p['prediction_performance']['coverage']['status']=='available'
    assert p['prediction_performance']['coverage']['value']['mean']==.125


def test_bad_runtime_and_error_metadata_remain_visible(memory):
    with memory.db:
        memory.db.execute("INSERT OR REPLACE INTO runtime VALUES(1,'{broken')")
        memory.db.execute("INSERT INTO events VALUES(1,5000,'ERROR','synthetic','private','{}')")
    tid=record(memory);assert update(memory,tid)=='updated'
    p=current(memory)
    assert p['memory']['runtime_reported']['status']=='error'
    assert p['recent_failures']['status']=='error'
    assert p['recent_failures']['value']['count']==1
    assert p['recent_failures']['value']['invalid_metadata_count']==1
    assert p['recent_failures']['value']['latest_valid_event'] is None


def test_b7_never_rolls_back_a_transaction_it_failed_to_acquire(memory):
    tid=record(memory)
    def authorizer(op,first,*args):
        if op==sqlite3.SQLITE_TRANSACTION and first=='BEGIN':return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    memory.db.set_authorizer(authorizer)
    try:assert update(memory,tid)=='failed'
    finally:memory.db.set_authorizer(None)
    assert current(memory) is None and not memory.db.in_transaction
    assert memory.db.execute('PRAGMA busy_timeout').fetchone()[0]==2000


class CleanupFailureConnection:
    """Inject one cleanup fault while keeping actual SQLite transactions observable."""
    def __init__(self, db, failure):
        self.db, self.failure = db, failure
        self.restoration_attempted = False
        self.rollback_calls = 0
        self.progress_removals = 0

    def __getattr__(self, name):
        return getattr(self.db, name)

    def execute(self, sql, *args):
        if sql == 'PRAGMA busy_timeout=2000':
            self.restoration_attempted = True
            if self.failure == 'timeout':
                raise sqlite3.DatabaseError('synthetic timeout cleanup failure')
        return self.db.execute(sql, *args)

    def rollback(self):
        self.rollback_calls += 1
        if self.failure == 'rollback' or self.failure == 'diagnostic_rollback' and self.rollback_calls == 2:
            raise sqlite3.DatabaseError('synthetic rollback cleanup failure')
        return self.db.rollback()

    def set_progress_handler(self, callback, n):
        if callback is None:
            self.progress_removals += 1
            if self.failure == 'progress':
                raise sqlite3.DatabaseError('synthetic progress cleanup failure')
        return self.db.set_progress_handler(callback, n)


@pytest.mark.parametrize('failure', ['timeout', 'rollback', 'progress', 'diagnostic_rollback'])
def test_cleanup_faults_are_diagnosed_without_escaping_or_skipping_other_cleanup(memory, monkeypatch, caplog, failure):
    import seed.self_model as module
    from threading import Thread
    tid=record(memory)
    original=memory.db
    proxy=CleanupFailureConnection(original, failure)
    if failure in ('rollback', 'diagnostic_rollback'):
        def invalid(*args):raise ValueError('synthetic invalid evidence')
        monkeypatch.setattr(module, 'build_snapshot', invalid)
    if failure == 'diagnostic_rollback':
        original.execute("CREATE TRIGGER fail_diagnostic BEFORE INSERT ON events WHEN NEW.category='SELF_MODEL' BEGIN SELECT RAISE(ABORT,'diagnostic failed'); END")
    memory.db=proxy
    try:
        assert update(memory,tid)=='failed'
        assert proxy.restoration_attempted
        assert proxy.progress_removals >= 1
        assert 'Self model' in caplog.text and 'cleanup' in caplog.text.lower()
        acquired=[]
        def check_lock():
            ok=memory._lock.acquire(blocking=False);acquired.append(ok)
            if ok:memory._lock.release()
        thread=Thread(target=check_lock);thread.start();thread.join()
        assert acquired==[True]
        assert original.execute('SELECT 1').fetchone()[0]==1
        if failure == 'rollback':
            # Ownership is uncertain: no second diagnostic transaction attempted.
            assert proxy.rollback_calls == 1
            assert not original.execute("SELECT 1 FROM events WHERE category='SELF_MODEL'").fetchone()
        if failure == 'timeout':
            # Commit happened, but failed cleanup must never report update success.
            assert current(memory)['source_transition_id']==tid
    finally:
        memory.db=original
        original.set_progress_handler(None,0)
        original.rollback()
        original.execute('PRAGMA busy_timeout=2000')


@pytest.mark.parametrize('interrupt', [KeyboardInterrupt, SystemExit])
def test_cleanup_failure_never_masks_interrupt(memory, monkeypatch, interrupt):
    import seed.self_model as module
    tid=record(memory);original=memory.db
    proxy=CleanupFailureConnection(original,'progress')
    def stop(*args):raise interrupt('synthetic interruption')
    monkeypatch.setattr(module,'build_snapshot',stop)
    memory.db=proxy
    try:
        with pytest.raises(interrupt,match='synthetic interruption'):update(memory,tid)
        assert proxy.restoration_attempted
        assert not original.in_transaction
    finally:
        memory.db=original
        original.set_progress_handler(None,0)
        original.rollback()
        original.execute('PRAGMA busy_timeout=2000')


@pytest.mark.parametrize('interrupt', [KeyboardInterrupt, SystemExit])
def test_interrupt_during_failure_diagnostic_still_restores_connection(memory, monkeypatch, interrupt):
    import seed.self_model as module
    tid=record(memory)
    def invalid(*args):raise ValueError('synthetic invalid evidence')
    def interrupt_diagnostic(*args):raise interrupt('synthetic diagnostic interruption')
    monkeypatch.setattr(module,'build_snapshot',invalid)
    monkeypatch.setattr(module,'emit',interrupt_diagnostic)
    with pytest.raises(interrupt,match='synthetic diagnostic interruption'):update(memory,tid)
    assert not memory.db.in_transaction
    assert memory.db.execute('PRAGMA busy_timeout').fetchone()[0]==2000
