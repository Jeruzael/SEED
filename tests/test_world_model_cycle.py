import json
import socket
import sqlite3
import pytest
from seed.memory import Memory
from seed.organism import SeedOrganism
from seed.world_model import WorldModel
from seed.learner import state_key
from tests.test_transition_cycle import BEFORE, AFTER
from tests.test_world_model import record, belief


def test_core_world_learning_follows_committed_transition(home,monkeypatch):
    states=iter([BEFORE,AFTER]*2)
    perceptions=[]
    def perceive(body):
        perceptions.append(1)
        return next(states)
    monkeypatch.setattr('seed.body.Body.perceive',perceive)
    core=SeedOrganism(home)
    trace=[]
    try:
        persist=core.memory.record_transition_experience
        model=getattr(core,'world_model',None)
        assert model is not None, 'B4 core must own a persistent world model'
        recover=model.recover
        def persist_spy(**kw):
            result=persist(**kw)
            trace.append('persist')
            return result
        def recover_spy():
            assert trace[-1]=='persist'
            assert not core.memory.db.in_transaction
            assert core.memory.db.execute('SELECT count(*) FROM world_model_queue').fetchone()[0]==1
            trace.append('model')
            return recover()
        monkeypatch.setattr(core.memory,'record_transition_experience',persist_spy)
        monkeypatch.setattr(model,'recover',recover_spy)
        core.learner.epsilon=0
        core.cycle().delay_seconds
        core.cycle().delay_seconds
        assert trace==['persist','model','persist','model']
        assert len(perceptions)==4
        assert belief(core.memory)['evidence_count']==2
        assert core.memory.db.execute('SELECT count(*) FROM world_model_processed').fetchone()[0]==2
        categories=[r[0] for r in core.memory.db.execute('SELECT category FROM events ORDER BY id')]
        assert categories.index('WORLD_MODEL') > categories.index('PREDICTION_ERROR')
    finally: core.close()


def test_restart_recovers_only_b4_queue_with_no_perceptions(home,monkeypatch):
    def denied(*args,**kw): raise AssertionError('No sensing or network allowed')
    monkeypatch.setattr('seed.body.Body.perceive',denied)
    monkeypatch.setattr(socket,'create_connection',denied)
    monkeypatch.setattr(socket,'getaddrinfo',denied)
    m=Memory(home/'memory.sqlite3')
    for _ in range(10): record(m,BEFORE,AFTER,eligible=False)
    for _ in range(2): record(m,BEFORE,AFTER)
    old=[tuple(r) for r in m.db.execute('SELECT * FROM transitions')]
    m.close()
    core=SeedOrganism(home)
    try:
        b=belief(core.memory)
        assert b is not None, 'Startup must recover explicitly queued evidence'
        assert b['evidence_count']==2
        assert b['source_first_transition_id']==11 and b['source_last_transition_id']==12
        assert [tuple(r) for r in core.memory.db.execute('SELECT * FROM transitions')]==old
    finally: core.close()


@pytest.mark.parametrize('action', ['observe','reflect','consolidate','rest'])
def test_world_state_does_not_change_predictor_error_policy_reward_or_delay(tmp_path,monkeypatch,action):
    def denied(*args,**kw): raise AssertionError('No model network allowed')
    monkeypatch.setattr(socket,'create_connection',denied)
    monkeypatch.setattr(socket,'getaddrinfo',denied)
    runs=[]
    for active in (False,True):
        home=tmp_path/str(active)
        m=Memory(home/'memory.sqlite3')
        for _ in range(4): record(m,BEFORE,AFTER,action,eligible=active)
        WorldModel(m).recover()
        assert (belief(m) is not None)==active
        m.upsert_concept('original',.5,8,{'mean_load_ratio':.4})
        m.db.execute("INSERT INTO concept_evidence VALUES('original',1,2,'[1]')")
        m.db.commit()
        oldconcepts=[tuple(r) for r in m.db.execute('SELECT * FROM concepts')]
        oldevidence=[tuple(r) for r in m.db.execute('SELECT * FROM concept_evidence')]
        m.close()
        states=iter([BEFORE,AFTER])
        perceptions=[]
        def perceive(body):
            perceptions.append(1)
            return next(states)
        monkeypatch.setattr('seed.body.Body.perceive',perceive)
        core=SeedOrganism(home)
        try:
            core.learner.epsilon=0
            core.memory.set_q(state_key(BEFORE),action,.7,4)
            delay=core.cycle().delay_seconds
            row=dict(core.memory.db.execute('SELECT * FROM transitions ORDER BY id DESC LIMIT 1').fetchone())
            runtime=json.loads(core.memory.db.execute('SELECT data_json FROM runtime').fetchone()[0])
            runs.append((row['action'],row['legacy_reward'],row['prediction_json'],row['prediction_error_json'],
                         core.memory.get_q(state_key(BEFORE),action),delay,runtime['last_decision'],
                         core.learner.epsilon,core.learner.alpha))
            assert len(perceptions)==2
            assert [tuple(r) for r in core.memory.db.execute('SELECT * FROM concepts')]==oldconcepts
            assert [tuple(r) for r in core.memory.db.execute('SELECT * FROM concept_evidence')]==oldevidence
        finally: core.close()
    assert runs[0]==runs[1]


def test_cycle_model_failure_leaves_real_transition_recoverable(home,monkeypatch):
    states=iter([BEFORE,AFTER])
    monkeypatch.setattr('seed.body.Body.perceive',lambda _:next(states))
    core=SeedOrganism(home)
    try:
        core.memory.db.execute("""CREATE TRIGGER fail_model BEFORE INSERT ON world_model_processed
                                 BEGIN SELECT RAISE(ABORT,'world failed'); END""")
        with pytest.raises(sqlite3.IntegrityError,match='world failed'): core.cycle().delay_seconds
        assert core.memory.db.execute('SELECT count(*) FROM transitions').fetchone()[0]==1
        assert core.memory.db.execute('SELECT count(*) FROM world_model_queue').fetchone()[0]==1
        assert core.memory.db.execute('SELECT count(*) FROM world_pending').fetchone()[0]==0
        core.memory.db.execute('DROP TRIGGER fail_model')
    finally: core.close()
    core=SeedOrganism(home)
    try:
        assert belief(core.memory,pending=True)['evidence_count']==1
        assert core.memory.db.execute('SELECT count(*) FROM world_model_queue').fetchone()[0]==0
    finally: core.close()
