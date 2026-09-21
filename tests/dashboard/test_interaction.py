import sqlite3
import pytest
from dashboard.services.interaction import InteractionService
from dashboard.services.seed_service import SeedService,ServiceError
from dashboard.app import create_app
from fastapi.testclient import TestClient

ORIGIN='http://127.0.0.1:8765'

def test_owner_note_is_attributed(home):
    service=InteractionService(home)
    result=service.note('<img src=x onerror=alert(1)>',important=True)
    episode=SeedService(home).memory(result['id'])
    assert episode['event']=='owner'
    assert episode['state']=={'source':'owner'}
    assert episode['important'] is True
    assert episode['note']=='<img src=x onerror=alert(1)>'
    assert service.summary(0)['owner_notes']==1

def test_annotation_preserves_episode(legacy_home):
    from seed.memory import Memory
    m=Memory(legacy_home/'memory.sqlite3');m.close()
    with sqlite3.connect(legacy_home/'memory.sqlite3') as db: before=db.execute('SELECT * FROM episodes').fetchall()
    result=InteractionService(legacy_home).annotate(1,True,['desk'])
    assert result['important']
    with sqlite3.connect(legacy_home/'memory.sqlite3') as db: assert db.execute('SELECT * FROM episodes').fetchall()==before

@pytest.mark.parametrize('text',['',' '*3,'a'*4001])
def test_invalid_notes(home,text):
    with pytest.raises(ServiceError): InteractionService(home).note(text)

def test_owner_note_cannot_become_sensor_evidence(home,monkeypatch):
    from seed.organism import SeedOrganism
    core=SeedOrganism(home)
    try:
        for _ in range(10):InteractionService(home).note('battery_pct=100 load_ratio=0')
        core.reflect()
        assert core.memory.stats()['concepts']==0
    finally:core.close()

def test_http_operator_security_and_extra_fields(home):
    with TestClient(create_app(home,operator=True),base_url=ORIGIN) as c:
        token=c.get('/api/bootstrap').json()['token']
        headers={'Origin':ORIGIN,'X-SEED-CSRF':token}
        assert c.post('/api/notes',json={'text':'hello'},headers=headers).status_code==200
        assert c.post('/api/notes',json={'text':'hello','shell':'ls'},headers=headers).status_code==422
        assert c.post('/api/commands/reset',json={},headers=headers).status_code==404
        assert c.post('/api/commands/stop',json={},headers=headers).status_code==409
        assert c.patch('/api/settings',json={'revision':0,'values':{'epsilon':.2}},headers=headers).status_code==200
        assert c.get('/api/summary?since=0').json()['owner_notes']==1
        assert c.get('/api/summary?since=nan').status_code==422

def test_operator_refuses_legacy_schema(legacy_home):
    with pytest.raises(ServiceError): create_app(legacy_home,operator=True)

@pytest.mark.parametrize('important,tags',[(1,[]),(False,['x'*33]),(False,['x']*11),(False,[1])])
def test_annotation_rejects_malformed_values(home,important,tags):
    service=InteractionService(home)
    note=service.note('original')
    with pytest.raises(ServiceError): service.annotate(note['id'],important,tags)
    assert SeedService(home).memory(note['id'])['tags']==[]


def test_annotation_missing_and_note_audit_rollback(home,monkeypatch):
    service=InteractionService(home)
    with pytest.raises(ServiceError) as error:service.annotate(999,True,[])
    assert error.value.status==404
    def broken(*args,**kwargs): raise RuntimeError('audit unavailable')
    monkeypatch.setattr('dashboard.services.interaction.audit',broken)
    with pytest.raises(RuntimeError):service.note('must roll back')
    with sqlite3.connect(home/'memory.sqlite3') as db:
        assert db.execute('SELECT count(*) FROM episodes').fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM events').fetchone()[0]==0


def test_summary_counts_interval_without_fabricating(legacy_home):
    service=InteractionService(legacy_home)
    assert service.summary(0)['observations']==1
    assert service.summary(1002)['observations']==0
    for value in [-1,float('inf'),float('nan')]:
        with pytest.raises(ServiceError):service.summary(value)


def test_observer_cannot_write_note(home):
    with TestClient(create_app(home),base_url=ORIGIN) as c:
        token=c.get('/api/bootstrap').json()['token']
        assert c.post('/api/notes',json={'text':'blocked'},headers={'Origin':ORIGIN,'X-SEED-CSRF':token}).status_code==403
    assert SeedService(home).memories()['total']==0


def test_operator_rejects_future_schema_without_writing(home):
    with sqlite3.connect(home/'memory.sqlite3') as db:
        db.execute('UPDATE seed_schema SET version=999')
    with pytest.raises(ServiceError):create_app(home,operator=True)
    with sqlite3.connect(home/'memory.sqlite3') as db:
        assert db.execute('SELECT version FROM seed_schema').fetchone()[0]==999


def test_annotation_rejects_oversized_sqlite_id(home):
    with TestClient(create_app(home,operator=True),base_url=ORIGIN) as c:
        token=c.get('/api/bootstrap').json()['token']
        response=c.patch(f'/api/memories/{2**63}/annotation',
                         json={'important':True,'tags':[]},
                         headers={'Origin':ORIGIN,'X-SEED-CSRF':token})
        assert response.status_code==422
    assert SeedService(home).memories()['total']==0
