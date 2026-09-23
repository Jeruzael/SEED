import json
import sqlite3
import pytest
from seed.memory import Memory
from seed.world_model import WorldModel
from tests.test_world_model import record,belief


def source(m,signal='battery_pct',scope='global',scope_value='',n=8,confidence=.4,contradictions=0,payload=None):
    tid=record(m,eligible=False)
    family='boolean_frequency' if signal=='network_reachable' else 'numeric_delta'
    if payload is None:
        payload=dict(true_count=n-2,false_count=2,probability_true=(n-2)/n) if family=='boolean_frequency' else dict(
            mean_delta=-.12,mean_absolute_delta=.19,min_delta=-1.,max_delta=.4)
    payload={**payload,'confidence_kind':'evidence_consistency'}
    with m.db:
        cursor=m.db.execute('''INSERT INTO world_beliefs(belief_key,signal,scope,scope_value,belief_type,
            value_json,evidence_count,contradiction_count,confidence,created_at,updated_at,
            source_first_transition_id,source_last_transition_id,model_version)
            VALUES(?,?,?,?,?,?,?,?,?,1,2,?,?,1)''',
            (f'1:{signal}:{scope}:{scope_value}:{family}',signal,scope,scope_value,family,
             json.dumps(payload),n,contradictions,confidence,tid,tid))
    return cursor.lastrowid


def semantics(m):
    return [dict(r) for r in m.db.execute('SELECT * FROM semantic_memories ORDER BY id')]


@pytest.fixture
def setup(home):
    from seed.semantic_memory import Consolidator
    m=Memory(home/'memory.sqlite3')
    now=[100.]
    yield m,Consolidator(m,clock=lambda:now[0]),now
    m.close()


@pytest.mark.parametrize('n,confidence,created',[(7,.95,0),(8,.29,0),(8,.30,1)])
def test_promotion_thresholds(setup,n,confidence,created):
    m,c,now=setup
    source(m,n=n,confidence=confidence)
    run=c.run()
    assert run['source_beliefs_examined']==1 and run['eligible_beliefs']==created
    assert run['created_count']==created and len(semantics(m))==created


@pytest.mark.parametrize('signal', ['battery_pct','load_ratio','disk_free_pct','network_reachable'])
@pytest.mark.parametrize('scope,value',[('global',''),('action','reflect')])
def test_payload_provenance_and_idempotency(setup,signal,scope,value):
    m,c,now=setup
    sid=source(m,signal,scope,value,contradictions=2)
    original=dict(m.db.execute('SELECT * FROM world_beliefs').fetchone())
    run=c.run(provenance='owner_requested')
    assert run['created_count']==1 and run['status']=='completed' and run['provenance']=='owner_requested'
    row=semantics(m)[0]
    assert row['revision']==1 and row['status']=='active'
    assert row['model']=='semantic_v1' and row['model_version']==1
    assert row['source_belief_id']==sid and row['source_belief_model_version']==1
    assert row['source_belief_updated_at']==2
    assert row['evidence_count']==8 and row['contradiction_count']==2 and row['confidence']==.4
    assert row['signal']==signal and row['scope']==scope and row['scope_value']==value
    payload=json.loads(row['payload_json'])
    expected=json.loads(original['value_json'])
    del expected['confidence_kind']
    expected['interpretation']='observed_boolean_frequency' if signal=='network_reachable' else 'observed_transition_delta'
    assert payload==expected
    before=semantics(m)
    now[0]+=100
    again=c.run()
    assert again['created_count']==again['revised_count']==again['weakened_count']==0
    assert again['unchanged_count']==1 and semantics(m)==before
    assert not m.db.execute('SELECT 1 FROM semantic_memory_history').fetchone()
    assert dict(m.db.execute('SELECT * FROM world_beliefs').fetchone())==original


@pytest.mark.parametrize('field,value',[('evidence_count',9),('contradiction_count',1),('confidence',.35),
    ('value_json','{"mean_delta":0,"mean_absolute_delta":1,"min_delta":-1,"max_delta":1,"confidence_kind":"evidence_consistency"}')])
def test_material_change_revises_even_when_source_timestamp_is_unchanged(setup,field,value):
    m,c,now=setup
    source(m)
    c.run()
    previous=semantics(m)[0]
    with m.db:m.db.execute(f'UPDATE world_beliefs SET {field}=?',(value,))
    now[0]+=1
    run=c.run()
    current=semantics(m)[0]
    assert run['revised_count']==1 and current['revision']==2
    assert current['created_at']==previous['created_at'] and current['updated_at']==101
    saved=json.loads(m.db.execute('SELECT record_json FROM semantic_memory_history').fetchone()[0])
    assert saved==previous
    assert c.run()['revised_count']==0


def test_timestamp_only_and_json_format_only_do_not_change_semantic_revision(setup):
    m,c,now=setup
    source(m)
    c.run()
    previous=semantics(m)
    raw=m.db.execute('SELECT value_json FROM world_beliefs').fetchone()[0]
    with m.db:m.db.execute('UPDATE world_beliefs SET updated_at=99,value_json=?',(json.dumps(json.loads(raw),sort_keys=True,indent=2),))
    assert c.run()['unchanged_count']==1
    assert semantics(m)==previous


def test_actual_contradictions_weaken_and_consistent_evidence_reactivates(setup):
    m,c,now=setup
    w=WorldModel(m)
    def add(delta):
        w.observe_transition(record(m,{'battery_pct':max(0,-delta)},{'battery_pct':max(0,delta)}))
    for _ in range(8):add(1)
    assert c.run()['created_count']==2
    for _ in range(18):
        add(-100 if belief(m)['value']['mean_delta']>0 else 100)
    assert belief(m)['confidence']<.30
    now[0]+=1
    assert c.run()['weakened_count']==2
    assert all(r['status']=='weakened' and r['revision']==2 for r in semantics(m))
    assert c.run()['weakened_count']==0
    add(1)
    assert belief(m)['confidence']>=.30
    now[0]+=1
    assert c.run()['revised_count']==2
    assert all(r['status']=='active' and r['revision']==3 for r in semantics(m))
    histories=[json.loads(r[0]) for r in m.db.execute('SELECT record_json FROM semantic_memory_history ORDER BY revision')]
    assert [r['status'] for r in histories]==['active','active','weakened','weakened']


@pytest.mark.parametrize('bad', ['{broken','[]','{"mean_delta":NaN}',
    '{"mean_delta":0,"mean_absolute_delta":-1,"min_delta":-1,"max_delta":1}',
    '{"mean_delta":4,"mean_absolute_delta":4,"min_delta":-1,"max_delta":1}'])
def test_malformed_item_reports_failure_continues_and_preserves_last_valid_semantics(setup,bad):
    m,c,now=setup
    a=source(m)
    c.run()
    old=semantics(m)[0]
    source(m,'network_reachable')
    with m.db:m.db.execute('UPDATE world_beliefs SET value_json=? WHERE id=?',(bad,a))
    run=c.run()
    assert run['failed_count']==1 and run['created_count']==1 and run['revised_count']==1
    assert run['status']=='completed_with_errors'
    updated=semantics(m)[0]
    assert updated['status']=='source_unavailable' and updated['revision']==2
    assert updated['payload_json']==old['payload_json'] and updated['confidence']==old['confidence']
    assert c.run()['revised_count']==0


@pytest.mark.parametrize('payload',[{'true_count':6,'false_count':3,'probability_true':.75},
    {'true_count':6,'false_count':2,'probability_true':.1},
    {'true_count':True,'false_count':7,'probability_true':.125}])
def test_invalid_boolean_counts_or_probability_never_promoted(setup,payload):
    m,c,now=setup
    source(m,'network_reachable',payload=payload)
    assert c.run()['failed_count']==1 and not semantics(m)


def test_revision_failure_rolls_back_history_current_cursor_and_success_counts(setup):
    m,c,now=setup
    source(m)
    c.run()
    old=semantics(m)
    state=tuple(m.db.execute('SELECT * FROM consolidation_state').fetchone())
    with m.db:
        m.db.execute('UPDATE world_beliefs SET evidence_count=9')
        m.db.execute("""CREATE TRIGGER fail_revision BEFORE UPDATE ON semantic_memories
                         BEGIN SELECT RAISE(ABORT,'revision failed'); END""")
    with pytest.raises(sqlite3.IntegrityError,match='revision failed'):c.run()
    assert semantics(m)==old
    assert not m.db.execute('SELECT 1 FROM semantic_memory_history').fetchone()
    assert tuple(m.db.execute('SELECT * FROM consolidation_state').fetchone())==state
    failed=dict(m.db.execute('SELECT * FROM consolidation_runs ORDER BY id DESC LIMIT 1').fetchone())
    assert failed['status']=='failed' and failed['created_count']==failed['revised_count']==0
    with m.db:m.db.execute('DROP TRIGGER fail_revision')
    assert c.run()['revised_count']==1


@pytest.mark.parametrize('state,reason',[({'load_ratio':.81},'high_load'),
    ({'battery_pct':19,'charging':False},'low_battery'),({'disk_free_pct':9},'low_disk')])
def test_resource_suppression_does_not_touch_semantics_or_sources(setup,state,reason):
    m,c,now=setup
    source(m)
    before=[tuple(r) for r in m.db.execute('SELECT * FROM world_beliefs')]
    run=c.run(state=state)
    assert run['status']=='suppressed' and run['result']['reason']==reason
    assert run['source_beliefs_examined']==0 and not semantics(m)
    assert before==[tuple(r) for r in m.db.execute('SELECT * FROM world_beliefs')]


@pytest.mark.parametrize('state',[{}, {'load_ratio':.8,'battery_pct':20,'charging':False,'disk_free_pct':10},
    {'load_ratio':float('inf'),'battery_pct':-1,'charging':False,'disk_free_pct':'1'},
    {'battery_pct':19,'charging':None},{'battery_pct':19,'charging':True}])
def test_unknown_and_boundary_resources_do_not_suppress(setup,state):
    m,c,now=setup
    source(m)
    assert c.run(state=state)['created_count']==1


def test_cyclic_cursor_revisits_old_changes_and_survives_restart(home,monkeypatch):
    import seed.semantic_memory as semantic
    monkeypatch.setattr(semantic,'RUN_LIMIT',3)
    m=Memory(home/'memory.sqlite3')
    for signal in ('battery_pct','load_ratio','disk_free_pct','network_reachable'):
        for action in ('observe','reflect'):source(m,signal,'action',action)
    c=semantic.Consolidator(m)
    first=c.run()
    assert first['result']['examined_ids']==[1,2,3] and first['created_count']==3
    m.close()
    m=Memory(home/'memory.sqlite3')
    try:
        c=semantic.Consolidator(m)
        assert c.run()['result']['examined_ids']==[4,5,6]
        with m.db:m.db.execute('UPDATE world_beliefs SET evidence_count=9 WHERE id=1')
        final=c.run()
        assert final['result']['examined_ids']==[7,8,1]
        assert final['created_count']==2 and final['revised_count']==1
        assert len(semantics(m))==8
    finally:m.close()


def test_hard100_bound_with_synthetic_overflow_and_no_raw_evidence_reads(setup):
    m,c,now=setup
    # Valid B4 identities are capped at20. Bypass scope CHECK only in this fixture
    # to verify100-item overflow/failure fairness without expanding production scope.
    m.db.execute('PRAGMA ignore_check_constraints=ON')
    for i in range(105):source(m,scope='action',scope_value=f'invalid{i}')
    m.db.execute('PRAGMA ignore_check_constraints=OFF')
    sql=[]
    m.db.set_trace_callback(sql.append)
    first=c.run()
    m.db.set_trace_callback(None)
    assert first['source_beliefs_examined']==first['failed_count']==100
    assert first['result']['examined_ids']==list(range(1,101))
    assert c.run()['result']['examined_ids'][:5]==list(range(101,106))
    assert not any('FROM transitions' in s or 'FROM episodes' in s for s in sql)


def test_equal_json_numbers_do_not_create_spurious_revision(setup):
    m,c,now=setup
    sid=source(m,payload=dict(mean_delta=1.,mean_absolute_delta=1.,min_delta=1.,max_delta=1.))
    c.run()
    previous=semantics(m)
    with m.db:m.db.execute('UPDATE world_beliefs SET value_json=? WHERE id=?',
        (json.dumps(dict(mean_delta=1,mean_absolute_delta=1,min_delta=1,max_delta=1,confidence_kind='evidence_consistency')),sid))
    assert c.run()['revised_count']==0
    assert semantics(m)==previous


def test_transaction_acquisition_failure_records_failed_audit_when_storage_recovers(setup):
    m,c,now=setup
    source(m)
    begins=[]
    def authorize(action,first,second,database,trigger):
        if action==sqlite3.SQLITE_TRANSACTION and first=='BEGIN':
            begins.append(first)
            if len(begins)==2:return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    m.db.set_authorizer(authorize)
    try:
        with pytest.raises(sqlite3.DatabaseError,match='not authorized'):c.run()
    finally:m.db.set_authorizer(None)
    run=c.get_run(1)
    assert run['status']=='failed' and run['completed_at']==100
    assert run['failed_count']==1 and run['created_count']==run['revised_count']==0
    assert not semantics(m)
    assert not m.db.execute('SELECT 1 FROM consolidation_state').fetchone()
    assert c.run()['created_count']==1
