import json
import sqlite3
import pytest
from seed.organism import SeedOrganism

STATE={'battery_pct':80,'charging':True,'load_ratio':.1,'disk_free_pct':75,'local_hour':12,'wall_time':1000}

@pytest.mark.parametrize('gap,expected_wakes',[(45,0),(45.01,1),(-10,0)])
def test_resume_inference_is_strict_gap_threshold(home,monkeypatch,gap,expected_wakes):
    monkeypatch.setattr('seed.body.Body.perceive',lambda self:dict(STATE))
    core=SeedOrganism(home)
    try:
        core.last_tick_wall=1000
        monkeypatch.setattr('seed.organism.time.time',lambda:1000+gap)
        core.infer_wake_if_needed()
        assert core.memory.db.execute("SELECT count(*) FROM episodes WHERE event='wake'").fetchone()[0]==expected_wakes
        if expected_wakes:
            event=core.memory.db.execute("SELECT data_json FROM events WHERE category='LIFECYCLE'").fetchone()
            assert json.loads(event[0])['inferred'] is True
    finally:core.close()


def test_b1_cycle_moves_legacy_learning_after_action_and_second_observation(home,monkeypatch):
    monkeypatch.setattr('seed.body.Body.perceive',lambda self:dict(STATE))
    core=SeedOrganism(home)
    try:
        core.learner.epsilon=0
        core.memory.set_q('charging|calm|ok|day','reflect',.7,4)
        delay=core.cycle()
        rows=core.memory.db.execute('SELECT category,data_json FROM events ORDER BY id').fetchall()
        assert [r[0] for r in rows]==['PERCEPTION','DECISION','ACTION','ACTION','PERCEPTION','LEARNING','MEMORY']
        assert json.loads(rows[5][1])['new_value']==pytest.approx(.655)
        assert json.loads(rows[2][1])['phase']=='start'
        assert json.loads(rows[3][1])['phase']=='complete'
        assert delay==12
        episode=core.memory.recent_episodes(1)[0]
        assert episode['action']=='reflect' and episode['reward']==.45
    finally:core.close()


def test_start_wait_heartbeat_stop_and_restart_preserve_identity(home,monkeypatch):
    perceived=[]
    def perceive(self):
        perceived.append(1)
        return dict(STATE)
    monkeypatch.setattr('seed.body.Body.perceive',perceive)
    monkeypatch.setattr('seed.learner.random.random',lambda:.9)
    monkeypatch.setattr('seed.learner.random.choice',lambda choices:choices[0])
    core=SeedOrganism(home)
    identity=core.identity.copy()
    heartbeats=[]
    original=core.telemetry.runtime
    def capture(**fields):
        if set(fields)=={'heartbeat'}:heartbeats.append(fields['heartbeat'])
        return original(**fields)
    core.telemetry.runtime=capture
    # Replace only the external wait, not the organism loop, cycle, or database.
    def wait_then_stop(timeout):
        assert 0<timeout<=2
        core.stop()
        return True
    monkeypatch.setattr(core.stop_event,'wait',wait_then_stop)
    core.run()
    assert heartbeats
    assert len(perceived)==3  # start + before/after; shutdown reuses recorded state
    with sqlite3.connect(home/'memory.sqlite3') as db:
        rows=db.execute('SELECT event,note FROM episodes ORDER BY id').fetchall()
        assert [r[0] for r in rows]==['wake','experience','sleep']
        assert rows[0][1]=='process_start' and rows[-1][1]=='process_stop'
        runtime=json.loads(db.execute('SELECT data_json FROM runtime').fetchone()[0])
        assert runtime['lifecycle']=='STOPPED'
    again=SeedOrganism(home)
    try:
        assert again.identity==identity
        assert again.memory.stats()['episodes']==3
    finally:again.close()
