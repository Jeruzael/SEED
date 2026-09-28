import json
import socket
import pytest
from seed.organism import SeedOrganism
from seed.learner import state_key
from tests.test_semantic_memory import source,semantics
from tests.test_transition_cycle import BEFORE,AFTER


def no_network(monkeypatch):
    def denied(*args,**kw):raise AssertionError('No consolidation network activity')
    for name in ('socket','create_connection','getaddrinfo'):monkeypatch.setattr(socket,name,denied)


def test_policy_consolidate_uses_fresh_before_state_and_keeps_checkpoint(home,monkeypatch):
    no_network(monkeypatch)
    states=iter([BEFORE,AFTER])
    perceptions=[]
    def perceive(body):
        perceptions.append(1)
        return next(states)
    monkeypatch.setattr('seed.body.Body.perceive',perceive)
    core=SeedOrganism(home)
    try:
        source(core.memory)
        core.memory.set_meta('last_state',{'load_ratio':9})
        core.learner.epsilon=0
        core.memory.set_q(state_key(BEFORE),'consolidate',.7,4)
        assert core.cycle().delay_seconds==20
        assert len(semantics(core.memory))==1, 'Existing consolidate must perform B6 semantic work'
        run=dict(core.memory.db.execute('SELECT * FROM consolidation_runs').fetchone())
        assert run['provenance']=='policy_selected' and run['status']=='completed'
        assert len(perceptions)==2
        assert core.memory.get_q(state_key(BEFORE),'consolidate')==pytest.approx((.574,5))
        transition=core.memory.db.execute('SELECT * FROM transitions ORDER BY id DESC LIMIT 1').fetchone()
        assert transition['action']=='consolidate' and transition['legacy_reward']==0
        checkpoint=core.memory.get_meta('last_consolidation')
        assert set(('at','episodes','concepts','run_id','status')) <= checkpoint.keys()
        assert checkpoint['run_id']==run['id'] and checkpoint['status']=='completed'
    finally:core.close()


def test_owner_same_engine_uses_latest_state_without_transition_or_reward(home,monkeypatch):
    no_network(monkeypatch)
    monkeypatch.setattr('seed.body.Body.perceive',lambda _:pytest.fail('Owner consolidation must not perceive'))
    core=SeedOrganism(home)
    try:
        source(core.memory)
        core.memory.set_meta('last_state',{'load_ratio':9})
        for i in range(2):
            if i:core.memory.set_meta('last_state',{'load_ratio':.1})
            core.memory.db.execute("INSERT INTO commands VALUES(?,'consolidate',?,0,99999999999,'pending',NULL)",
                                   (str(i),core.session_id))
            core.memory.db.commit()
            core.process_commands()
        runs=[dict(r) for r in core.memory.db.execute('SELECT * FROM consolidation_runs ORDER BY id')]
        assert len(runs)==2, 'Owner consolidate must invoke the same B6 engine'
        assert [r['status'] for r in runs]==['suppressed','completed']
        assert all(r['provenance']=='owner_requested' for r in runs)
        assert len(semantics(core.memory))==1
        assert core.memory.db.execute('SELECT count(*) FROM q_values').fetchone()[0]==0
        assert core.memory.db.execute('SELECT count(*) FROM transitions').fetchone()[0]==1  # source fixture only
        assert core.memory.db.execute('SELECT count(*) FROM curiosity_assessments').fetchone()[0]==0
    finally:core.close()


def test_b8_excludes_suppressed_autonomous_consolidate_preserving_owner_guard(home,monkeypatch):
    high={**BEFORE,'load_ratio':.81}
    monkeypatch.setattr('seed.body.Body.perceive',lambda _:dict(high))
    core=SeedOrganism(home)
    try:
        source(core.memory)
        core.learner.epsilon=0
        core.memory.set_q(state_key(high),'consolidate',100,4)
        core.memory.set_q(state_key(high),'rest',1,0)
        assert core.cycle().delay_seconds==35
        assert core.memory.get_meta('last_action')=='rest'
        assert core.memory.db.execute('SELECT count(*) FROM consolidation_runs').fetchone()[0]==0
        assert core.memory.get_q(state_key(high),'consolidate')==(100,4)
        assert core.memory.get_q(state_key(high),'rest')==(1,1)
        run=core.consolidate(state=high,provenance='owner_requested')
        assert run['status']=='suppressed' and not semantics(core.memory)
    finally:core.close()


def test_no_startup_wake_shutdown_or_curiosity_consolidation(home,monkeypatch):
    monkeypatch.setattr('seed.body.Body.perceive',lambda _:dict(BEFORE))
    core=SeedOrganism(home)
    try:
        source(core.memory)
        core.awaken()
        core.reflect(provenance='curiosity_triggered')
        core.sleep()
        assert core.memory.db.execute('SELECT count(*) FROM consolidation_runs').fetchone()[0]==0
    finally:core.close()
    core=SeedOrganism(home)
    try:assert core.memory.db.execute('SELECT count(*) FROM consolidation_runs').fetchone()[0]==0
    finally:core.close()


@pytest.mark.parametrize('action',['observe','reflect','consolidate','rest'])
def test_semantic_state_has_no_upstream_influence_or_memory_deletion(tmp_path,monkeypatch,action):
    from seed.semantic_memory import Consolidator
    results=[]
    for promoted in (False,True):
        states=iter([BEFORE,AFTER])
        monkeypatch.setattr('seed.body.Body.perceive',lambda _:next(states))
        core=SeedOrganism(tmp_path/str(promoted))
        try:
            source(core.memory)
            preserved=('episodes','transitions','world_beliefs','world_pending','world_model_processed',
                       'curiosity_assessments','curiosity_runtime','concepts','concept_evidence','q_values','meta')
            before={t:[tuple(r) for r in core.memory.db.execute(f'SELECT * FROM {t}')] for t in preserved}
            if promoted:
                Consolidator(core.memory).run()
                assert len(semantics(core.memory))==1
                assert {t:[tuple(r) for r in core.memory.db.execute(f'SELECT * FROM {t}')] for t in preserved}==before
            core.learner.epsilon=0
            core.memory.set_q(state_key(BEFORE),action,.7,4)
            delay=core.cycle().delay_seconds
            r=dict(core.memory.db.execute('SELECT * FROM transitions ORDER BY id DESC LIMIT 1').fetchone())
            curiosity=dict(core.memory.db.execute('SELECT * FROM curiosity_assessments').fetchone())
            for key in ('created_at','claimed_at','completed_at'):curiosity.pop(key)
            results.append((r['action'],r['legacy_reward'],r['prediction_json'],r['prediction_error_json'],curiosity,
                            core.memory.get_q(state_key(BEFORE),action),core.learner.epsilon,core.learner.alpha,delay))
        finally:core.close()
    assert results[0]==results[1]
