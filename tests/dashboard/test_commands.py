import json
import sqlite3
import pytest
from dashboard.command_broker.broker import CommandBroker
from dashboard.services.seed_service import SeedService,ServiceError
from seed.commands import CommandQueue
from seed.organism import SeedOrganism

class FakeProcess:
    def status(self): return {'state':'unknown','pid':None}
    def start(self): return {'state':'running'}
    def stop(self): return {'state':'unregistered'}
    def restart(self): return {'state':'running'}

@pytest.fixture
def broker(home):
    service=SeedService(home,process=FakeProcess())
    return CommandBroker(service,service.process)

@pytest.mark.parametrize('name',['sh','observe; touch /tmp/seed-injection','reset','delete_memories','factory_reset'])
def test_unknown_command(broker,name):
    with pytest.raises(ServiceError) as e: broker.request(name,confirmation='RESET SEED')
    assert e.value.code=='unknown_command'

def test_confirmation_and_stopped(broker):
    with pytest.raises(ServiceError) as e: broker.request('stop',confirmation='restart')
    assert e.value.code=='confirmation_required'
    with pytest.raises(ServiceError) as e: broker.request('reflect')
    assert e.value.code=='core_unavailable'
    assert broker.request('stop',confirmation='stop')['result']['state']=='unregistered'

def test_queue_only_runs_in_core(home,monkeypatch):
    monkeypatch.setattr('seed.body.Body.perceive',lambda self:{'load_ratio':.1,'wall_time':123})
    core=SeedOrganism(home)
    try:
        core.telemetry.runtime(lifecycle='AWAKE')
        service=SeedService(home,process=FakeProcess());b=CommandBroker(service,service.process)
        result=b.request('observe')
        assert core.memory.stats()['episodes']==0
        core.process_commands()
        assert core.memory.stats()['episodes']==1
        assert b.result(result['id'])['status']=='complete'
        core.process_commands()
        assert core.memory.stats()['episodes']==1
    finally: core.close()

def test_old_session_requests_not_replayed(home):
    from seed.memory import Memory
    m=Memory(home/'memory.sqlite3')
    with m.db:
        m.db.execute("INSERT INTO commands VALUES('old','observe','prior',1,99999999999,'running',NULL)")
        m.db.execute("INSERT INTO commands VALUES('pending','observe','prior',1,99999999999,'pending',NULL)")
    CommandQueue(m).recover('new')
    assert CommandQueue(m).claim('new') is None
    assert m.db.execute("SELECT status FROM commands WHERE id='old'").fetchone()[0]=='interrupted'
    m.close()

def test_expired_and_stop_discard_queue(home,monkeypatch):
    monkeypatch.setattr('seed.body.Body.perceive',lambda self:{})
    core=SeedOrganism(home)
    try:
        with core.memory.db:
            core.memory.db.execute("INSERT INTO commands VALUES('expired','observe',?,1,2,'pending',NULL)",(core.session_id,))
        core.process_commands()
        assert core.memory.db.execute("SELECT status FROM commands WHERE id='expired'").fetchone()[0]=='expired'
        core.stop()
        core.process_commands()
        assert core.memory.stats()['episodes']==0
    finally: core.close()
