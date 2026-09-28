import json
import sqlite3
from contextlib import contextmanager
import pytest
from seed.organism import SeedOrganism
from tests.test_decision import STATE, RNG
from tests.dashboard.test_curiosity import client
from dashboard.services.read_store import ReadStore, ServiceError
from dashboard.services.decisions import DecisionReadService

@pytest.fixture
def recorded(home,monkeypatch):
    monkeypatch.setattr('seed.body.Body.perceive',lambda _:dict(STATE))
    monkeypatch.setattr('seed.organism.time.time',lambda:100.)
    core=SeedOrganism(home)
    core.decisions.rng=RNG()
    core.learner.epsilon=0
    for _ in range(3):core.cycle()
    core.close()
    return home

def test_list_detail_and_inclusive_corrupt_pagination(recorded):
    c=client(recorded)
    with sqlite3.connect(recorded/'memory.sqlite3') as db:
        db.execute("UPDATE decision_records SET data_json='broken' WHERE transition_id=2")
        before=list(db.iterdump())
    r=c.get('/api/decisions?limit=2')
    assert r.status_code==200
    data=r.json()
    assert [x['transition_id'] for x in data['items']]==[3,2] and data['next_cursor']==1
    assert data['items'][1]==dict(available=False,status='error',reason='invalid_decision',transition_id=2)
    assert c.get('/api/decisions?before=1&limit=2').json()['items'][0]['transition_id']==1
    detail=c.get('/api/decisions/3').json()
    assert detail['record']['transition_id']==3 and detail['available']
    assert 'prediction' not in detail['record']
    assert c.get('/api/decisions/2').json()['record'] is None
    assert c.get('/api/decisions/4').status_code==404
    with sqlite3.connect(recorded/'memory.sqlite3') as db:assert list(db.iterdump())==before

@pytest.mark.parametrize('query',['limit=0','limit=51','limit=true','limit=1.0','limit=1&limit=2','before=0',
    'before=9223372036854775808','after=1','action=rest'])
def test_http_query_contract(recorded,query):
    assert client(recorded).get('/api/decisions?'+query).status_code==422

@pytest.mark.parametrize('value',[True,0,-1,1.,'1',float('nan'),2**63])
def test_direct_cursor_contract(recorded,value):
    with pytest.raises(ServiceError) as err:DecisionReadService(ReadStore(recorded)).list(before=value)
    assert err.value.status==422
    with pytest.raises(ServiceError):DecisionReadService(ReadStore(recorded)).detail(value)

@pytest.mark.parametrize('damage',['digest','state','duplicate','unknown','bool','oversize','mirror','source_clock'])
def test_corruption_never_returns_partial_trusted_payload(recorded,damage):
    with sqlite3.connect(recorded/'memory.sqlite3') as db:
        raw=db.execute('SELECT data_json FROM decision_records WHERE transition_id=3').fetchone()[0]
        data=json.loads(raw)
        if damage=='digest':data['selected_prediction_sha256']='0'*64
        if damage=='state':data['current']['battery_pct']=70
        if damage=='unknown':data['extra']=1
        if damage=='bool':data['random_draw']=False
        if damage=='source_clock':data['candidates']['observe']['resource_forecasts']['battery_pct']['newest_source_completed_at']=101
        raw=json.dumps(data)
        if damage=='duplicate':raw=raw[:-1]+',"model_version":1}'
        if damage=='oversize':
            db.execute('PRAGMA ignore_check_constraints=ON');raw=' '*16385
        db.execute('UPDATE decision_records SET data_json=? WHERE transition_id=3',(raw,))
        if damage=='mirror':db.execute("UPDATE decision_records SET selected_action='rest' WHERE transition_id=3")
    response=client(recorded).get('/api/decisions/3')
    assert response.status_code==200 and response.json()==dict(available=False,status='error',reason='invalid_decision',transition_id=3,record=None)


def test_missing_legacy_future_and_missing_table(tmp_path,recorded):
    absent=tmp_path/'absent'
    assert client(absent).get('/api/decisions').json()['reason']=='missing_home'
    assert not absent.exists()
    c=client(recorded)
    with sqlite3.connect(recorded/'memory.sqlite3') as db:db.execute('UPDATE seed_schema SET version=6')
    assert c.get('/api/decisions').json()['reason']=='legacy_schema'
    with sqlite3.connect(recorded/'memory.sqlite3') as db:db.execute('UPDATE seed_schema SET version=8')
    assert c.get('/api/decisions').status_code==409
    with sqlite3.connect(recorded/'memory.sqlite3') as db:
        db.execute('UPDATE seed_schema SET version=7');db.execute('DROP TABLE decision_records')
    assert c.get('/api/decisions').json()['reason']=='missing_decision_table'


def test_reader_is_bounded_readonly_and_does_not_rescore(recorded,monkeypatch):
    from seed import decision
    store=ReadStore(recorded);original=store.connection;queries=[]
    @contextmanager
    def traced():
        with original() as db:
            db.set_trace_callback(queries.append)
            yield db
    store.connection=traced
    def forbidden(*a,**kw):pytest.fail('observer must not compute or construct core')
    monkeypatch.setattr(decision,'components',forbidden)
    monkeypatch.setattr('seed.predictor.Predictor.predict_candidates',forbidden)
    monkeypatch.setattr('seed.memory.Memory.__init__',forbidden)
    data=DecisionReadService(store).list(limit=2)
    assert data['available'] and len([q for q in queries if q.upper().startswith('SELECT')])==4
    assert 'BEGIN' in queries and 'PRAGMA busy_timeout=0' in queries
    assert len(json.dumps(data,separators=(',',':')).encode())<=53248
    queries.clear()
    assert DecisionReadService(store).detail(3)['available']
    assert len([q for q in queries if q.upper().startswith('SELECT')])==3
