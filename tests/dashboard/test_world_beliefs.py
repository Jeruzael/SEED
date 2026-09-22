import json
import sqlite3
import pytest
from fastapi.testclient import TestClient
from dashboard.app import create_app
from dashboard.services.seed_service import SeedService
from dashboard.services.read_store import ServiceError
from seed.memory import Memory
from seed.world_model import WorldModel
from tests.test_world_model import record


def populate(home):
    m=Memory(home/'memory.sqlite3')
    w=WorldModel(m)
    for action in ('observe','reflect'):
        for _ in range(2):
            w.observe_transition(record(m,{'battery_pct':80},{'battery_pct':79,'network':True},action))
    m.close()


def test_readonly_pagination_filter_detail_and_legacy_empty(tmp_path,legacy_home):
    home=tmp_path/"world"
    populate(home)
    with sqlite3.connect(home/'memory.sqlite3') as db: before=list(db.iterdump())
    client=TestClient(create_app(home),base_url="http://127.0.0.1:8765")
    response=client.get('/api/world-beliefs?limit=2')
    assert response.status_code==200
    first=response.json()
    assert first['available'] is True and len(first['items'])==2
    second=client.get('/api/world-beliefs',params={'limit':2,'after':first['next_cursor']}).json()
    assert first['items'][-1]['id'] < second['items'][0]['id']
    last=client.get('/api/world-beliefs',params={'limit':2,'after':second['next_cursor']}).json()
    assert len(last['items'])==2 and last['next_cursor'] is None
    filtered=client.get('/api/world-beliefs?signal=battery_pct&scope=action&scope_value=reflect').json()
    assert len(filtered['items'])==1
    b=filtered['items'][0]
    assert b['value']['mean_delta']==-1 and b['evidence_count']==2
    assert b['confidence']==.1 and b['contradiction_count']==0
    assert b['source_first_transition_id']==3 and b['source_last_transition_id']==4
    assert b['confidence_kind']=='evidence_consistency'
    assert client.get(f"/api/world-beliefs/{b['id']}").json()==b
    assert client.get('/api/world-beliefs/999').status_code==404
    with sqlite3.connect(home/'memory.sqlite3') as db: assert list(db.iterdump())==before
    legacy=TestClient(create_app(legacy_home),base_url="http://127.0.0.1:8765")
    assert legacy.get('/api/world-beliefs').json()=={'available':False,'items':[],'next_cursor':None}
    assert legacy.get('/api/world-beliefs/1').status_code==404
    with sqlite3.connect(legacy_home/'memory.sqlite3') as db:
        assert not db.execute("SELECT 1 FROM sqlite_master WHERE name='world_beliefs'").fetchone()


@pytest.mark.parametrize('query', ['limit=0','limit=101','after=-1','after=9223372036854775808',
                                  'signal=hostname','scope=context','scope_value=unknown'])
def test_invalid_read_queries_rejected(home,query):
    assert TestClient(create_app(home),base_url="http://127.0.0.1:8765").get('/api/world-beliefs?'+query).status_code==422


@pytest.mark.parametrize('id', ['-1','0','9223372036854775808'])
def test_invalid_detail_ids_rejected(home,id):
    assert TestClient(create_app(home),base_url="http://127.0.0.1:8765").get('/api/world-beliefs/'+id).status_code==422


def test_service_itself_bounds_calls_and_uses_readonly_connection(home):
    service=SeedService(home)
    assert hasattr(service,'world_beliefs'), 'B4 requires a bounded inspection service'
    with pytest.raises(ServiceError): service.world_beliefs(limit=101)
    with pytest.raises(ServiceError): service.world_belief(2**63)
    with service.store.connection() as db:
        with pytest.raises(sqlite3.OperationalError,match='readonly'):
            db.execute("DELETE FROM world_beliefs")


def test_operator_rejects_missing_model_tables_without_migration(home):
    with sqlite3.connect(home/'memory.sqlite3') as db:
        db.execute('DROP TABLE world_model_processed')
    with pytest.raises(ServiceError,match='schema'):
        create_app(home,operator=True)
