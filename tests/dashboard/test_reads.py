import json
import sqlite3
import time
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

def test_stale_runtime_not_sleeping(home):
    from seed.memory import Memory
    from seed.telemetry import Telemetry
    m=Memory(home/'memory.sqlite3')
    Telemetry(m).runtime(heartbeat=time.time()-100, lifecycle='AWAKE', pid=999999, session_id='other')
    m.close()
    status=SeedService(home).status()
    assert status['lifecycle'] is None
    assert status['fresh'] is False

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
