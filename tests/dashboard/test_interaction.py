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
