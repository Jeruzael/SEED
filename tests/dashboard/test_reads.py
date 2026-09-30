import json
import sqlite3
import time
from types import SimpleNamespace
import pytest
from dashboard.services.seed_service import SeedService, ServiceError

def test_missing_home_not_created(tmp_path):
    path=tmp_path/'missing'
    assert SeedService(path).status()['data_state']=='missing'
    assert not path.exists()

def test_legacy_reads_preserve_schema(legacy_home):
    service=SeedService(legacy_home)
    with sqlite3.connect(legacy_home/'memory.sqlite3') as db:
        before=db.execute('SELECT sql FROM sqlite_master').fetchall()
    assert service.memories(page_size=1)['total']==1
    assert service.memory(1)['state']['battery_pct']==80
    assert service.concepts()['items'][0]['evidence']==10
    assert service.learning()['last_decision'] is None
    assert service.status()['compatibility']=='legacy'
    assert service.environment()['state']['load_ratio']==.1
    assert service.development()['observations']==1
    with sqlite3.connect(legacy_home/'memory.sqlite3') as db:
        assert db.execute('SELECT sql FROM sqlite_master').fetchall()==before

@pytest.mark.parametrize('kwargs',[{'sort':'id; DROP TABLE episodes'},{'page_size':101},{'page':0}])
def test_invalid_queries(legacy_home,kwargs):
    with pytest.raises(ServiceError):
        SeedService(legacy_home).memories(**kwargs)

def test_search_injection_is_literal(legacy_home):
    service=SeedService(legacy_home)
    assert service.memories(search="' OR 1=1 --")['total']==0
    assert service.memories(event='sleep')['total']==0
    assert service.memories(sort='oldest')['items'][0]['id']==1
    assert service.memories(sort='reward')['items'][0]['reward']==.45

def test_corrupt_and_bad_json(legacy_home,tmp_path):
    with sqlite3.connect(legacy_home/'memory.sqlite3') as db:
        db.execute("UPDATE episodes SET state_json='oops'")
    assert SeedService(legacy_home).memory(1)['warning']
    path=tmp_path/'bad'
    path.mkdir()
    (path/'memory.sqlite3').write_bytes(b'not a database')
    assert SeedService(path).status()['data_state']=='error'

@pytest.fixture
def no_host_process(monkeypatch):
    def unexpected_status(*args, **kwargs):
        raise AssertionError('stale-runtime unit test must not inspect host LaunchAgent')
    monkeypatch.setattr('dashboard.services.process.ProcessController.status', unexpected_status)

def test_stale_runtime_not_sleeping(home, no_host_process):
    from seed.memory import Memory
    from seed.telemetry import Telemetry
    m=Memory(home/'memory.sqlite3')
    Telemetry(m).runtime(heartbeat=time.time()-100, lifecycle='AWAKE', pid=999999, session_id='other')
    m.close()
    process=SimpleNamespace(status=lambda: {'state':'unknown', 'reason':'Synthetic test process'})
    status=SeedService(home, process=process).status()
    assert status['lifecycle'] is None
    assert status['fresh'] is False

@pytest.mark.parametrize('process_state', ['unregistered', 'loaded'])
def test_stale_runtime_with_inactive_launchagent_is_stopped(home, no_host_process, process_state):
    from seed.memory import Memory
    from seed.telemetry import Telemetry
    m=Memory(home/'memory.sqlite3')
    Telemetry(m).runtime(heartbeat=time.time()-100, lifecycle='AWAKE', pid=999999, session_id='other')
    m.close()
    process=SimpleNamespace(status=lambda: {'state':process_state, 'pid':None})
    status=SeedService(home, process=process).status()
    assert status['lifecycle']=='STOPPED'
    assert status['fresh'] is False
    assert status['reason']=='LaunchAgent is not running; no active core lock.'

def test_storage_excludes_symlinks(home,tmp_path):
    outside=tmp_path/'large'
    outside.write_bytes(b'x'*100000)
    (home/'link').symlink_to(outside)
    result=SeedService(home).storage()
    assert result['other_bytes']==0
    assert result['database_bytes']>0

def test_event_cursor_gap_and_reset(home):
    from seed.memory import Memory
    from seed.telemetry import Telemetry
    m=Memory(home/'memory.sqlite3'); t=Telemetry(m)
    for _ in range(5): t.emit('SYSTEM','test','event',{})
    with m.db: m.db.execute('DELETE FROM events WHERE id<4')
    m.close()
    service=SeedService(home)
    assert service.events(after=1)['gap']
    assert service.events(after=99)['reset']
    assert [e['id'] for e in service.events(after=4)['items']]==[5]


def evidence_fixture(home):
    from seed.memory import Memory
    from seed.semantic_memory import Consolidator
    from tests.test_semantic_memory import source
    from tests.test_curiosity_attention import store
    m=Memory(home/'memory.sqlite3')
    source(m);source(m,signal='network_reachable')
    store(m);store(m)
    engine=Consolidator(m,clock=lambda:100)
    engine.run()
    m.db.execute('UPDATE world_beliefs SET confidence=.2');m.db.commit();engine.run()
    m.db.execute('UPDATE world_beliefs SET confidence=.4');m.db.commit();engine.run()
    m.close()


@pytest.mark.parametrize('table,column,route,payload',[
    ('world_beliefs','value_json','/api/world-beliefs','value'),
    ('curiosity_assessments','components_json','/api/curiosity','components'),
    ('semantic_memories','payload_json','/api/semantic-memories','payload'),
    ('semantic_memory_history','record_json','/api/semantic-memories/1/history','record'),
    ('consolidation_runs','result_json','/api/consolidation-runs','result')])
@pytest.mark.parametrize('bad',['broken','{"x":1,"x":2}',' '*32769])
def test_model_corruption_is_visible_and_consumes_page_slot(home,table,column,route,payload,bad):
    from tests.dashboard.test_curiosity import client
    evidence_fixture(home)
    with sqlite3.connect(home/'memory.sqlite3') as db:
        db.execute(f'UPDATE {table} SET {column}=?',(bad,));before=list(db.iterdump())
    r=client(home).get(route+'?limit=1')
    assert r.status_code==200
    page=r.json();assert len(page['items'])==1
    item=page['items'][0]
    assert item['read_status']=='corrupt' and item[payload] is None
    assert page['next_cursor'] is not None
    with sqlite3.connect(home/'memory.sqlite3') as db:assert list(db.iterdump())==before


def test_curiosity_corrupt_window_never_refills(home):
    from seed.memory import Memory
    from tests.test_curiosity_attention import store
    m=Memory(home/'memory.sqlite3')
    for _ in range(101):store(m,score=.4,level='NOTABLE')
    m.db.execute("UPDATE curiosity_assessments SET components_json='broken' WHERE transition_id=101")
    m.db.commit();m.close()
    summary=SeedService(home).curiosity_summary()
    assert summary['assessment_count']==100 and summary['valid_assessment_count']==99
    assert summary['corrupt_assessment_count']==1 and summary['counts_by_level']=={'NOTABLE':99}
    assert summary['mean_score']==pytest.approx(.4)


def test_model_query_budgets_and_scalar_corruption(home,monkeypatch):
    from contextlib import contextmanager
    evidence_fixture(home);service=SeedService(home);sql=[];original=service.store.connection
    @contextmanager
    def tracked(*a,**kw):
        with original(*a,**kw) as db:
            db.set_trace_callback(sql.append);yield db
    monkeypatch.setattr(service.store,'connection',tracked)
    for operation,max_selects in [(lambda:service.world_beliefs(),4),
        (lambda:service.curiosity_assessments(),4),(lambda:service.semantic_memories(),4),
        (lambda:service.semantic_memory(1),3),(lambda:service.semantic_history(1),4),
        (lambda:service.consolidation_runs(),4),(lambda:service.curiosity_summary(),3)]:
        sql.clear();operation()
        assert len([s for s in sql if s.upper().startswith('SELECT')])<=max_selects
        assert any('busy_timeout=0' in s for s in sql)
        assert any('ROLLBACK' in s for s in sql)
    with sqlite3.connect(home/'memory.sqlite3') as db:
        db.execute("UPDATE world_beliefs SET updated_at='bad'")
    assert service.world_belief(1)['read_status']=='corrupt'
    assert service.semantic_memory(1)['source_status']=='source_unavailable'


@pytest.mark.parametrize('route,table', [('/api/world-beliefs','world_beliefs'),
    ('/api/curiosity','curiosity_assessments'),('/api/semantic-memories','semantic_memories'),
    ('/api/consolidation-runs','consolidation_runs')])
def test_supporting_schema_missing_table_is_not_legacy(home,route,table):
    from tests.dashboard.test_curiosity import client
    with sqlite3.connect(home/'memory.sqlite3') as db:db.execute(f'DROP TABLE {table}')
    data=client(home).get(route).json()
    assert data['status']=='error' and data['reason']=='missing_feature_table'
    with sqlite3.connect(home/'memory.sqlite3') as db:db.execute('UPDATE seed_schema SET version=8')
    assert client(home).get(route).status_code==409


def test_semantic_history_nested_payload_and_corrupt_source(home):
    evidence_fixture(home)
    with sqlite3.connect(home/'memory.sqlite3') as db:
        raw=json.loads(db.execute('SELECT record_json FROM semantic_memory_history WHERE semantic_memory_id=1 AND revision=1').fetchone()[0])
        raw['payload_json']=raw['payload_json']+' '*300
        db.execute('UPDATE semantic_memory_history SET record_json=? WHERE semantic_memory_id=1 AND revision=1',(json.dumps(raw),))
        db.execute("UPDATE world_beliefs SET value_json='broken' WHERE id=1")
    service=SeedService(home)
    current=service.semantic_memory(1)
    assert current['payload']['mean_delta']==-.12 and current['source_status']=='source_unavailable'
    history=service.semantic_history(1,before=1)
    assert history['items'][0]['record']['payload']['mean_delta']==-.12


def test_development_budget_is_independent_and_readonly(home,monkeypatch):
    from seed.memory import Memory
    from dashboard.services import seed_service
    m=Memory(home/'memory.sqlite3')
    m.db.executemany("INSERT INTO episodes(ts,event,state_json,action,reward,note) VALUES(1,'experience','{}','observe',0,'')",[()]*1000)
    m.db.commit();before=list(m.db.iterdump());m.close()
    monkeypatch.setattr(seed_service,'DEVELOPMENT_READ_BUDGET',1,raising=False)
    with pytest.raises(ServiceError) as error:SeedService(home).development()
    assert error.value.code=='development_read_unavailable' and error.value.status==503
    with sqlite3.connect(home/'memory.sqlite3') as db:assert list(db.iterdump())==before
    monkeypatch.setattr(seed_service,'DEVELOPMENT_READ_BUDGET',300000)
    assert SeedService(home).development()['observations']==1000


def test_episode_detail_bounds_and_timeline_are_explicit(legacy_home):
    with sqlite3.connect(legacy_home/'memory.sqlite3') as db:
        db.execute('UPDATE episodes SET state_json=?,note=?',(' '*16385,'x'*4097))
        db.execute("INSERT INTO episodes(ts,event,state_json,action,reward,note) VALUES(2,'wake','{}','observe',0,?)",('x'*4097,))
    service=SeedService(legacy_home);item=service.memory(1)
    assert item['read_status']=='corrupt' and item['warning'] and item['note'] is None
    timeline=service.development()['timeline']
    assert timeline[0]['note'] is None and timeline[0]['read_status']=='corrupt'


@pytest.mark.parametrize('kind,table,column,value',[
    ('world','world_beliefs','confidence',float('inf')),
    ('world','world_beliefs','model_version','bad'),
    ('curiosity','curiosity_assessments','failure_reason','x'*257),
    ('curiosity','curiosity_assessments','components_json','{"signals":{"battery_pct":{"sample":"bad"}}}'),
    ('semantic','semantic_memories','source_fingerprint','z'*64),
    ('run','consolidation_runs','result_json','{"examined_ids":["bad"],"failures":[],"reason":null}'),
    ('world','world_beliefs','value_json','{"x":"'+'é'*200+'"}'),
])
def test_model_typed_domains_and_bounds(home,kind,table,column,value):
    evidence_fixture(home)
    with sqlite3.connect(home/'memory.sqlite3') as db:
        db.execute('PRAGMA ignore_check_constraints=ON')
        db.execute(f'UPDATE {table} SET {column}=?',(value,))
    s=SeedService(home)
    result={'world':lambda:s.world_belief(1),'curiosity':lambda:s.curiosity_assessments()['items'][0],
            'semantic':lambda:s.semantic_memory(1),'run':lambda:s.consolidation_runs()['items'][0]}[kind]()
    assert result['read_status']=='corrupt'


def test_missing_database_read_error_codes(tmp_path):
    s=SeedService(tmp_path/'absent')
    for operation,code in [(s.world_beliefs,'evidence_read_unavailable'),
        (s.development,'development_read_unavailable'),(lambda:s.memory(1),'memory_read_unavailable')]:
        with pytest.raises(ServiceError) as error:operation()
        assert error.value.code==code and error.value.status==503


@pytest.mark.parametrize('status,score,level',[
    ('unavailable',.4,'UNAVAILABLE'),('unavailable',None,'HIGH'),
    ('evaluated',None,'HIGH'),('evaluated',.4,'UNAVAILABLE')])
def test_curiosity_contradictory_status_score_level_is_corrupt(home,status,score,level):
    evidence_fixture(home)
    with sqlite3.connect(home/'memory.sqlite3') as db:
        db.execute('PRAGMA ignore_check_constraints=ON')
        db.execute('UPDATE curiosity_assessments SET status=?,score=?,level=?',(status,score,level))
        before=list(db.iterdump())
    s=SeedService(home);page=s.curiosity_assessments(limit=1)
    assert page['items'][0]['read_status']=='corrupt' and page['items'][0]['components'] is None
    assert page['next_cursor'] is not None
    summary=s.curiosity_summary()
    assert summary['assessment_count']==2 and summary['valid_assessment_count']==0
    assert summary['mean_score'] is None
    with sqlite3.connect(home/'memory.sqlite3') as db:assert list(db.iterdump())==before
