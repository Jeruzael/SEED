import json
import os
import subprocess
import sys
import pytest
from seed.memory import Memory
from seed.learner import Learner, state_key
from seed.organism import SeedOrganism

STATE = {'battery_pct':80,'charging':True,'load_ratio':.1,'disk_free_pct':75,'local_hour':12,'wall_time':1001}

def test_decision_keeps_preupdate_values(home):
    m = Memory(home/'memory.sqlite3')
    try:
        m.set_q(state_key(STATE),'reflect',.7,4)
        learner = Learner(m,epsilon=0)
        decision = learner.choose(STATE)
        learner.update(decision,.45)
        assert decision.action == 'reflect'
        assert decision.exploration is False
        assert decision.values['reflect'] == .7
        assert decision.visits['reflect'] == 4
        value, visits = m.get_q(state_key(STATE),'reflect')
        assert value == pytest.approx(.655)
        assert visits == 5
    finally:
        m.close()

def test_exploration_and_ties(home,monkeypatch):
    m = Memory(home/'memory.sqlite3')
    try:
        learner = Learner(m,epsilon=1)
        d = learner.choose(STATE)
        assert d.exploration and len(d.candidates)==4
        learner.epsilon=0
        assert len(learner.choose(STATE).candidates)==4
    finally:
        m.close()

def test_cycle_emits_real_chain_and_evidence(home,monkeypatch):
    monkeypatch.setattr('seed.body.Body.perceive',lambda self:dict(STATE))
    organism = SeedOrganism(home)
    try:
        organism.learner.epsilon=0
        organism.memory.set_q(state_key(STATE),'reflect',.7,4)
        for _ in range(8):
            organism.memory.episode('experience',STATE)
        assert organism.cycle()==12
        types=[r[0] for r in organism.memory.db.execute('SELECT category FROM events ORDER BY id')]
        assert all(t in types for t in ['PERCEPTION','DECISION','LEARNING','ACTION','MEMORY','CONCEPT'])
        rt=json.loads(organism.memory.db.execute('SELECT data_json FROM runtime').fetchone()[0])
        assert rt['activity']=='idle' and rt['last_action']=='reflect'
        evidence=organism.memory.db.execute('SELECT episode_ids_json FROM concept_evidence').fetchone()[0]
        assert len(json.loads(evidence))==8
        with pytest.raises(RuntimeError):
            SeedOrganism(home)
    finally:
        organism.close()

def test_startup_failure_releases_lock(home,monkeypatch):
    def broken(self):
        raise RuntimeError('sensor failed')
    monkeypatch.setattr('seed.body.Body.perceive',broken)
    organism=SeedOrganism(home)
    with pytest.raises(RuntimeError,match='sensor failed'):
        organism.run()
    other=SeedOrganism(home)
    other.close()

def test_import_main_has_no_side_effects(tmp_path):
    target=tmp_path/'absent'
    result=subprocess.run([sys.executable,'-c','import main'],env=dict(os.environ,SEED_HOME=str(target)),capture_output=True,text=True,timeout=5)
    assert result.returncode==0,result.stderr
    assert not target.exists()
