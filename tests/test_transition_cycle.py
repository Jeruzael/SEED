"""Real autonomous cycles; only external sensing/clock and random choice are fixed."""
import json
import sqlite3
import pytest
from seed.organism import SeedOrganism
from seed.learner import state_key

BEFORE = {'battery_pct':80,'charging':True,'load_ratio':.1,'disk_free_pct':75,
          'local_hour':12,'wall_time':1000,'load_5m_ratio':.2,'network':False,
          'hostname':'synthetic','machine':'synthetic','macos':'synthetic'}
AFTER = {**BEFORE, 'battery_pct':10,'charging':False,'load_ratio':1,
         'disk_free_pct':5,'wall_time':1002}


@pytest.mark.parametrize('action,reward,delay', [('observe',.45,8),('reflect',.45,12),
                                                ('consolidate',0,20),('rest',0,35)])
def test_cycle_observes_outcome_before_legacy_learning(home, monkeypatch, action, reward, delay):
    trace, buffer = [], {}
    now = [1000.0]
    monkeypatch.setattr('seed.organism.time.time', lambda:now[0])
    def perceive(_body):
        phase = 'before' if not trace else 'after'
        trace.append(phase)
        buffer.clear()
        buffer.update(BEFORE if phase == 'before' else AFTER)
        now[0] = buffer['wall_time']
        return buffer  # intentionally reused; core must preserve its first snapshot
    monkeypatch.setattr('seed.body.Body.perceive', perceive)
    core = SeedOrganism(home)
    try:
        core.learner.epsilon = 0
        core.memory.set_q(state_key(BEFORE), action, .7, 4)
        choose, evaluate, update = core.decisions.select, core.learner.reward, core.learner.update
        def choose_traced(state):
            trace.append('choose')
            return choose(state)
        def reward_traced(state, selected):
            trace.append('reward')
            assert state == BEFORE
            return evaluate(state, selected)
        def update_traced(decision, value):
            trace.append('update')
            return update(decision, value)
        monkeypatch.setattr(core.decisions, 'select', choose_traced)
        monkeypatch.setattr(core.learner, 'reward', reward_traced)
        monkeypatch.setattr(core.learner, 'update', update_traced)
        perform = getattr(core, 'perform_action', None)
        def action_traced(selected, state=None):
            trace.append('action')
            assert selected == action
            assert core.memory.get_q(state_key(BEFORE), action) == (.7,4)
            return perform(selected, state=state)
        monkeypatch.setattr(core, 'perform_action', action_traced, raising=False)
        assert core.cycle().delay_seconds == delay
        assert trace == ['before','choose','reward','action','after','reward','update']
        assert core.memory.get_q(state_key(BEFORE), action) == pytest.approx((.7+.18*(reward-.7),5))
        row = core.memory.db.execute('SELECT * FROM transitions').fetchone()
        assert json.loads(row['state_before_json']) == BEFORE
        assert json.loads(row['state_after_json']) == AFTER
        assert row['started_at'] == 1000 and row['completed_at'] == 1002
        assert row['legacy_reward'] == reward
        assert json.loads(row['prediction_json'])['action'] == action
        assert json.loads(row['prediction_error_json'])['evaluator'] == 'prediction_error_v1'
        assert core.memory.get_meta('last_state') == AFTER
        events = [(r[0],json.loads(r[1])) for r in core.memory.db.execute(
            'SELECT category,data_json FROM events ORDER BY id')]
        phases = [data['phase'] for category,data in events if category == 'PERCEPTION']
        assert phases == ['before_action','after_action']
        learning = next(data for category,data in events if category == 'LEARNING')
        assert learning['transition_id'] == row['id']
        rt = json.loads(core.memory.db.execute('SELECT data_json FROM runtime').fetchone()[0])
        assert rt['last_reward'] == reward and rt['last_completed_action'] == action
        assert rt['current_action'] is None and rt['last_successful_cycle'] == 1002
        assert rt['last_decision']['score'] == .7
        assert rt['activity'] == ('resting' if action == 'rest' else 'idle')
    finally:
        core.close()


@pytest.mark.parametrize('failure', ['action','after','invalid_after'])
def test_failed_action_or_post_observation_never_learns_or_records_success(home, monkeypatch, failure):
    calls = []
    def perceive(_body):
        calls.append(1)
        if len(calls) == 2:
            if failure == 'after': raise OSError('sensor failure')
            if failure == 'invalid_after': return {'load_ratio':float('nan')}
        return dict(BEFORE)
    monkeypatch.setattr('seed.body.Body.perceive', perceive)
    core = SeedOrganism(home)
    try:
        core.learner.epsilon = 0
        core.memory.set_q(state_key(BEFORE),'reflect',.7,4)
        monkeypatch.setattr(core, 'awaken', lambda: None)
        monkeypatch.setattr(core.stop_event, 'wait', lambda timeout: core.stop())
        if failure == 'action':
            def broken(): raise OSError('action failure')
            monkeypatch.setattr(core, 'reflect', broken)
        with pytest.raises((OSError,ValueError)):
            core.run()
        # run() closes storage and records ERROR; inspect temporary database independently.
        with sqlite3.connect(home / 'memory.sqlite3') as db:
            assert db.execute('SELECT value,visits FROM q_values').fetchone() == (.7,4)
            assert db.execute('SELECT count(*) FROM transitions').fetchone()[0] == 0
            assert db.execute("SELECT count(*) FROM episodes WHERE event='experience'").fetchone()[0] == 0
            assert db.execute("SELECT count(*) FROM events WHERE category='LEARNING'").fetchone()[0] == 0
            rt = json.loads(db.execute('SELECT data_json FROM runtime').fetchone()[0])
            assert rt['lifecycle'] == 'ERROR'
    finally:
        core.close()


@pytest.mark.parametrize('action', ['observe','reflect','consolidate'])
def test_owner_commands_never_become_autonomous_transitions(home, monkeypatch, action):
    monkeypatch.setattr('seed.body.Body.perceive', lambda self:dict(BEFORE))
    core = SeedOrganism(home)
    try:
        with core.memory.db:
            core.memory.db.execute("INSERT INTO commands VALUES('owner',?,?,0,99999999999,'pending',NULL)",
                                   (action,core.session_id))
        core.process_commands()
        assert core.memory.db.execute('SELECT status FROM commands').fetchone()[0] == 'complete'
        assert core.memory.db.execute('SELECT count(*) FROM transitions').fetchone()[0] == 0
        assert core.memory.db.execute('SELECT count(*) FROM q_values').fetchone()[0] == 0
        if action == 'observe':
            assert core.memory.recent_episodes(1)[0]['note'] == 'source=owner_command'
    finally:
        core.close()
