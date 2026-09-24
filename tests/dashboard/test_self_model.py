import json
import sqlite3
import pytest
from dashboard.app import create_app
from dashboard.services.seed_service import SeedService
from dashboard.services.read_store import ServiceError
from tests.dashboard.test_curiosity import client
from seed.memory import Memory
from tests.test_self_model import record,update,current


def publish(home):
    m=Memory(home/'memory.sqlite3')
    tid=record(m);assert update(m,tid)=='updated'
    p=current(m);m.close();return p


def test_current_projection_uses_readonly_store_and_never_process_or_core(home,monkeypatch):
    p=publish(home)
    with sqlite3.connect(home/'memory.sqlite3') as db:before=list(db.iterdump())
    def forbidden(*a,**kw):raise AssertionError('observer must not construct core or inspect process')
    monkeypatch.setattr('seed.memory.Memory.__init__',forbidden)
    monkeypatch.setattr('dashboard.services.process.ProcessController.status',forbidden)
    c=client(home);c.app.state.service.clock=lambda:1061
    response=c.get('/api/self-model')
    assert response.status_code==200
    body=response.json()
    assert body['available'] and body['status']=='stored'
    assert body['snapshot']['observations']['network']['status']=='stale'
    assert body['snapshot']['measured_at']==p['measured_at'] and body['read_at']==1061
    with sqlite3.connect(home/'memory.sqlite3') as db:assert list(db.iterdump())==before
    assert c.get('/api/self-model?limit=1').status_code==422
    assert c.post('/api/self-model').status_code in (403,405)


def test_empty_and_legacy_are_explicit_without_migration(tmp_path,legacy_home):
    home=tmp_path/'current'
    Memory(home/'memory.sqlite3').close()
    assert client(home).get('/api/self-model').json()['reason']=='awaiting_first_cycle'
    with sqlite3.connect(legacy_home/'memory.sqlite3') as db:before=list(db.iterdump())
    body=client(legacy_home).get('/api/self-model').json()
    assert body['available'] is False and body['reason']=='legacy_schema'
    with sqlite3.connect(legacy_home/'memory.sqlite3') as db:assert list(db.iterdump())==before
    with sqlite3.connect(home/'memory.sqlite3') as db:db.execute('UPDATE seed_schema SET version=5')
    assert client(home).get('/api/self-model').json()['reason']=='legacy_schema'


@pytest.mark.parametrize('damage',['json','nested','column','table','source','oversize','future','ambiguous'])
def test_corruption_and_incompatible_versions_are_not_available(home,damage):
    p=publish(home)
    with sqlite3.connect(home/'memory.sqlite3') as db:
        if damage=='json':db.execute("UPDATE self_model_current SET data_json='broken'")
        if damage=='nested':
            p['observations']['load_ratio']['value']=-1
            db.execute('UPDATE self_model_current SET data_json=?',(json.dumps(p),))
        if damage=='column':db.execute('UPDATE self_model_current SET updated_at=900')
        if damage=='table':db.execute('DROP TABLE self_model_current')
        if damage=='source':db.execute('DELETE FROM transitions')
        if damage=='oversize':
            db.execute('PRAGMA ignore_check_constraints=ON')
            db.execute('UPDATE self_model_current SET data_json=?',(' '*40000,))
        if damage=='future':db.execute('UPDATE seed_schema SET version=7')
        if damage=='ambiguous':db.execute('INSERT INTO seed_schema VALUES(6)')
    r=client(home).get('/api/self-model')
    if damage in ('future','ambiguous'):
        assert r.status_code==409
        assert r.json()['error']['code']=='incompatible_schema'
    else:
        assert r.status_code==200 and r.json()['status']=='error'
        assert r.json()['snapshot'] is None


def test_missing_home_and_operator_table_guard(tmp_path,home):
    absent=tmp_path/'missing'
    assert client(absent).get('/api/self-model').status_code==503
    assert not absent.exists()
    with sqlite3.connect(home/'memory.sqlite3') as db:db.execute('DROP TABLE self_model_current')
    with pytest.raises(ServiceError):create_app(home,operator=True)


def test_read_query_budget_and_sql_write_denial(home):
    from contextlib import contextmanager
    from dashboard.services.read_store import ReadStore
    from dashboard.services.self_model import SelfModelReadService
    publish(home);store=ReadStore(home);queries=[]
    original=store.connection
    @contextmanager
    def observed():
        with original() as db:
            db.set_trace_callback(queries.append)
            denied={sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE,sqlite3.SQLITE_CREATE_TABLE,sqlite3.SQLITE_DROP_TABLE}
            db.set_authorizer(lambda operation,*args:sqlite3.SQLITE_DENY if operation in denied else sqlite3.SQLITE_OK)
            yield db
    store.connection=observed
    result=SelfModelReadService(store,clock=lambda:1002).get()
    assert result['available']
    assert len([q for q in queries if q.startswith('SELECT')])==4
    assert len(json.dumps(result).encode())<=40960


def test_clock_rollback_projects_error_without_mutating_source(home):
    p=publish(home)
    s=SeedService(home,clock=lambda:999)
    result=s.self_model()
    assert result['snapshot']['observations']['network']['status']=='error'
    assert result['snapshot']['measured_at']==p['measured_at']
    with sqlite3.connect(home/'memory.sqlite3') as db:
        assert json.loads(db.execute('SELECT data_json FROM self_model_current').fetchone()[0])==p
