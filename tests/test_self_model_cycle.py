import json
from unittest.mock import patch
import pytest
from seed.organism import SeedOrganism
from seed.learner import state_key
from tests.test_self_model import STATE,current,record,update


def test_exact_downstream_slot_persisted_state_and_no_owner_or_restart_trigger(home,monkeypatch):
    monkeypatch.setattr('seed.body.Body.perceive',lambda _:dict(STATE))
    monkeypatch.setattr('seed.organism.time.time',lambda:1002)
    core=SeedOrganism(home)
    try:
        assert current(core.memory) is None
        core.memory.db.execute("INSERT INTO commands VALUES('owner','observe',?,0,999999,'pending',NULL)",(core.session_id,))
        core.memory.db.commit();core.process_commands()
        assert current(core.memory) is None
        core.learner.epsilon=0;core.memory.set_q(state_key(STATE),'observe',.7,4)
        core.cycle()
        p=current(core.memory)
        assert p is not None,'normal cycle must publish a B7 snapshot'
        assert p['source_transition_id']==1
        assert p['memory']['runtime_reported']['value']['last_successful_cycle'] is None
        events=[r[0] for r in core.memory.db.execute('SELECT category FROM events ORDER BY id')]
        assert events[-1]=='SELF_MODEL' and events.count('SELF_MODEL')==1
        assert core.memory.get_meta('last_state')==STATE
        assert json.loads(core.memory.db.execute('SELECT data_json FROM runtime').fetchone()[0])['last_successful_cycle']==1002
        saved=current(core.memory)
    finally:core.close()
    core=SeedOrganism(home)
    try:assert current(core.memory)==saved
    finally:core.close()


@pytest.mark.parametrize('action',['observe','reflect','consolidate','rest'])
@pytest.mark.parametrize('enabled',[False,True])
def test_snapshot_presence_corruption_and_failure_never_change_upstream_outputs(tmp_path,monkeypatch,action,enabled):
    results=[]
    for label in ('absent','present','corrupt','failed','noop'):
        perceptions=[]
        def perceive(_):perceptions.append(1);return dict(STATE)
        monkeypatch.setattr('seed.body.Body.perceive',perceive)
        monkeypatch.setattr('seed.organism.time.time',lambda:1002)
        core=SeedOrganism(tmp_path/label)
        try:
            old=record(core.memory)
            if label in ('present','corrupt'):
                update(core.memory,old)
                if label=='corrupt':
                    with core.memory.db:core.memory.db.execute("UPDATE self_model_current SET data_json='broken'")
            if label=='failed':
                core.memory.db.execute("CREATE TRIGGER block_snapshot BEFORE INSERT ON self_model_current BEGIN SELECT RAISE(ABORT,'blocked'); END")
            if label=='noop':
                monkeypatch.setattr(core.self_model,'update',lambda *a:'skipped')
            with core.memory.db:core.memory.db.execute('INSERT INTO settings VALUES(1,1,?)',
                (json.dumps({'epsilon':0,'prediction_error_curiosity':enabled}),))
            core.memory.set_q(state_key(STATE),action,.7,4)
            delays=[core.cycle(),core.cycle()]
            tables=('q_values','transitions','curiosity_assessments','world_beliefs','world_pending',
                    'world_model_processed','world_model_queue','semantic_memories','semantic_memory_history',
                    'consolidation_runs','concepts','concept_evidence')
            results.append(({t:[tuple(r) for r in core.memory.db.execute(f'SELECT * FROM {t} ORDER BY rowid')] for t in tables},
                            delays,len(perceptions),core.learner.epsilon,core.learner.alpha))
            assert len(perceptions)==4
        finally:core.close()
    assert all(r==results[0] for r in results)


def test_update_follows_attention_and_stop_remains_authoritative(home,monkeypatch):
    monkeypatch.setattr('seed.body.Body.perceive',lambda _:dict(STATE))
    monkeypatch.setattr('seed.organism.time.time',lambda:1002)
    core=SeedOrganism(home)
    try:
        execute=core.curiosity_attention.execute
        def attention(*args,**kw):
            result=execute(*args,**kw)
            # Deliberately change meta; B7 must use committed transition after-state.
            core.memory.set_meta('last_state',{'battery_pct':1})
            return result
        monkeypatch.setattr(core.curiosity_attention,'execute',attention)
        core.cycle()
        assert current(core.memory)['observations']['battery_pct']['value']==80
        assert core.memory.get_meta('last_state')=={'battery_pct':1}
        old=current(core.memory)
        def stopping(*args,**kw):core.stop()
        monkeypatch.setattr(core.curiosity_attention,'execute',stopping)
        core.cycle()
        assert current(core.memory)==old and core.stop_event.is_set()
    finally:core.close()


def test_normal_cycle_keeps_exactly_two_existing_network_probes(home,monkeypatch):
    import socket
    import seed.body as body
    probes=[]
    class Connection:
        def __enter__(self):return self
        def __exit__(self,*args):return False
    def connect(address,timeout):
        probes.append((address,timeout));return Connection()
    monkeypatch.setattr(socket,'create_connection',connect)
    from types import SimpleNamespace
    monkeypatch.setattr(body,'battery_state',lambda:(80,True))
    monkeypatch.setattr(body.shutil,'disk_usage',lambda _:SimpleNamespace(total=100,free=70))
    monkeypatch.setattr(body.os,'getloadavg',lambda:(.2,.3,.4))
    monkeypatch.setattr(body.os,'cpu_count',lambda:1)
    monkeypatch.setattr(body.platform,'node',lambda:'synthetic')
    monkeypatch.setattr(body.platform,'machine',lambda:'synthetic')
    monkeypatch.setattr(body.platform,'mac_ver',lambda:('synthetic',(),''))
    monkeypatch.setattr(body.time,'time',lambda:1002)
    localtime=body.time.localtime
    monkeypatch.setattr(body.time,'localtime',lambda *args:localtime(1002))
    core=SeedOrganism(home)
    try:
        core.cycle()
        assert current(core.memory) is not None
        assert probes==[(('1.1.1.1',443),1.0)]*2
    finally:core.close()
