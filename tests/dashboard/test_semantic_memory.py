import json
import sqlite3
import pytest
from seed.memory import Memory
from seed.semantic_memory import Consolidator
from tests.test_semantic_memory import source
from tests.dashboard.test_curiosity import client
from dashboard.services.seed_service import SeedService
from dashboard.services.read_store import ServiceError
from dashboard.app import create_app


def test_reads_filters_history_runs_and_preservation(home):
    m=Memory(home/'memory.sqlite3')
    source(m)
    source(m,signal='network_reachable',scope='action',scope_value='reflect')
    engine=Consolidator(m,clock=lambda:100)
    engine.run()
    m.db.execute("UPDATE world_beliefs SET confidence=.2 WHERE id=1")
    m.db.commit()
    engine.run(provenance='owner_requested')
    m.db.execute("UPDATE world_beliefs SET confidence=.4 WHERE id=1")
    m.db.commit()
    engine.run()
    before=list(m.db.iterdump())
    m.close()
    c=client(home)
    first=c.get('/api/semantic-memories?limit=1').json()
    assert first['available'] and len(first['items'])==1
    item=first['items'][0]
    assert item['revision']==3 and item['payload']['interpretation']=='observed_transition_delta'
    assert item['source_status']=='available'
    assert c.get('/api/semantic-memories/1').json()==item
    assert c.get('/api/semantic-memories',params={'after':first['next_cursor']}).json()['items'][0]['id']==2
    assert c.get('/api/semantic-memories?signal=network_reachable&scope=action&status=active').json()['items'][0]['id']==2
    assert not c.get('/api/semantic-memories?status=weakened').json()['items']
    h=c.get('/api/semantic-memories/1/history?limit=1').json()
    assert h['items'][0]['record']['status']=='weakened'
    assert h['items'][0]['record']['revision']==2
    assert h['items'][0]['record']['payload']['mean_delta']==-.12
    assert c.get('/api/semantic-memories/1/history',params={'before':h['next_cursor']}).json()['items'][0]['revision']==1
    runs=c.get('/api/consolidation-runs?limit=1').json()
    assert runs['items'][0]['id']==3 and runs['items'][0]['revised_count']==1
    assert c.get('/api/consolidation-runs',params={'before':runs['next_cursor']}).json()['items'][0]['id']==2
    with sqlite3.connect(home/'memory.sqlite3') as db:assert list(db.iterdump())==before


@pytest.mark.parametrize('corrupt',[False,True])
def test_missing_or_corrupt_source_reported_without_erasing_semantic(home,corrupt):
    m=Memory(home/'memory.sqlite3')
    source(m)
    Consolidator(m).run()
    if corrupt:m.db.execute("UPDATE world_beliefs SET value_json='broken'")
    else:
        m.db.commit()
        m.db.execute('PRAGMA foreign_keys=OFF')
        m.db.execute('DELETE FROM world_beliefs')  # simulate unexpected external damage only
    m.db.commit()
    before=list(m.db.iterdump())
    m.close()
    item=client(home).get('/api/semantic-memories/1').json()
    assert item['source_status']=='source_unavailable'
    assert item['status']=='active' and item['revision']==1
    assert item['payload']['mean_delta']==-.12
    with sqlite3.connect(home/'memory.sqlite3') as db:assert list(db.iterdump())==before


def test_legacy_no_migration(legacy_home):
    c=client(legacy_home)
    with sqlite3.connect(legacy_home/'memory.sqlite3') as db:before=list(db.iterdump())
    for route in ('semantic-memories','consolidation-runs'):
        assert c.get('/api/'+route).json()=={'available':False,'items':[],'next_cursor':None}
    for route in ('semantic-memories/1','semantic-memories/1/history'):
        assert c.get('/api/'+route).status_code==404
    with sqlite3.connect(legacy_home/'memory.sqlite3') as db:assert list(db.iterdump())==before


@pytest.mark.parametrize('route',[
    'semantic-memories?limit=101','semantic-memories?after=-1',
    'semantic-memories?signal=madeup','semantic-memories?scope=causal','semantic-memories?status=truth',
    'semantic-memories/0','semantic-memories/9223372036854775808',
    'semantic-memories/1/history?limit=0','semantic-memories/1/history?before=-1',
    'consolidation-runs?limit=101','consolidation-runs?before=9223372036854775808'])
def test_api_bounds(home,route):
    assert client(home).get('/api/'+route).status_code==422


def test_service_bounds_and_operator_schema(home):
    s=SeedService(home)
    for call in (lambda:s.semantic_memories(limit=101),lambda:s.semantic_memory(0),
                 lambda:s.semantic_history(1,limit=101),lambda:s.consolidation_runs(before=-1)):
        with pytest.raises(ServiceError):call()
    with sqlite3.connect(home/'memory.sqlite3') as db:db.execute('DROP TABLE consolidation_state')
    with pytest.raises(ServiceError,match='schema'):create_app(home,operator=True)
