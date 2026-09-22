import json
import sqlite3
from types import SimpleNamespace
import pytest
from seed.memory import Memory
from seed.organism import SeedOrganism
from seed.learner import state_key
from tests.test_transition_cycle import BEFORE, AFTER
from tests.test_predictor import history


def test_prospective_order_and_exact_pre_action_payload(home, monkeypatch):
    trace, observed = [], []
    states = iter([BEFORE, AFTER])
    def perceive(_body):
        state = dict(next(states))
        trace.append('before' if not observed else 'after')
        observed.append(state)
        return state
    monkeypatch.setattr('seed.body.Body.perceive', perceive)
    core = SeedOrganism(home)
    try:
        core.learner.epsilon = 0
        core.memory.set_q(state_key(BEFORE),'reflect',.7,4)
        for _ in range(2): history(core.memory, {'battery_pct':80}, {'battery_pct':79})
        from seed.predictor import Predictor
        # Attach before B2 integration exists, so failure is missing invocation, not a missing attribute.
        predictor = Predictor(core.memory)
        original_predict = predictor.predict
        predicted = []
        def predict(state, action):
            trace.append('prediction')
            assert len(observed) == 1 and state == BEFORE and action == 'reflect'
            result = original_predict(state, action)
            predicted.append(result.to_dict())
            return result
        monkeypatch.setattr(predictor,'predict',predict)
        monkeypatch.setattr(core,'predictor',predictor,raising=False)
        choose, perform = core.learner.choose, core.perform_action
        reward, update = core.learner.reward, core.learner.update
        persist = core.memory.record_transition_experience
        def choose_traced(state):
            trace.append('decision')
            return choose(state)
        def act(action):
            trace.append('action')
            perform(action)
            # New history would change a recomputed estimate; the stored one must stay prospective.
            for _ in range(2): history(core.memory, {'battery_pct':70}, {'battery_pct':75}, 'reflect')
        def evaluate(state, action):
            trace.append('reward')
            return reward(state, action)
        def learn(decision, value):
            trace.append('update')
            return update(decision, value)
        def store(**kwargs):
            trace.append('persistence')
            return persist(**kwargs)
        monkeypatch.setattr(core.learner,'choose',choose_traced)
        monkeypatch.setattr(core,'perform_action',act)
        monkeypatch.setattr(core.learner,'reward',evaluate)
        monkeypatch.setattr(core.learner,'update',learn)
        monkeypatch.setattr(core.memory,'record_transition_experience',store)
        assert core.cycle() == 12
        assert trace == ['before','decision','prediction','action','after','reward','update','persistence']
        assert len(predicted) == 1 and len(observed) == 2
        stored = core.memory.db.execute('SELECT * FROM transitions ORDER BY id DESC LIMIT 1').fetchone()
        payload = json.loads(stored['prediction_json'])
        assert payload == predicted[0]
        assert payload['signals']['battery_pct']['value'] == 79
        assert payload['signals']['battery_pct']['evidence_count'] == 2
        assert stored['prediction_error_json'] is None
        events = [(r[0],json.loads(r[1])) for r in core.memory.db.execute(
            'SELECT category,data_json FROM events ORDER BY id')]
        assert [category for category,_ in events] == ['PERCEPTION','DECISION','PREDICTION','ACTION',
                                                       'ACTION','PERCEPTION','LEARNING','MEMORY']
        assert events[2][1] == payload
    finally:
        core.close()


@pytest.mark.parametrize('action,reward,delay', [('observe',.45,8),('reflect',.45,12),
                                                ('consolidate',0,20),('rest',0,35)])
def test_prediction_values_do_not_influence_policy_reward_update_or_delay(home, monkeypatch, action, reward, delay):
    calls = []
    def perceive(_body):
        calls.append(1)
        return dict(BEFORE)
    monkeypatch.setattr('seed.body.Body.perceive',perceive)
    core = SeedOrganism(home)
    try:
        core.learner.epsilon = 0
        core.memory.set_q(state_key(BEFORE),action,.7,4)
        payload = {'model':'isolation_test','action':action,'signals':{
            'battery_pct':{'status':'predicted','value':0},
            'load_ratio':{'status':'predicted','value':1000000}}}
        monkeypatch.setattr(core,'predictor',SimpleNamespace(
            predict=lambda state,selected:SimpleNamespace(to_dict=lambda:payload)),raising=False)
        assert core.cycle() == delay
        row = core.memory.db.execute('SELECT * FROM transitions').fetchone()
        assert row['action'] == action and row['legacy_reward'] == reward
        assert core.memory.get_q(state_key(BEFORE),action) == pytest.approx((.7+.18*(reward-.7),5))
        assert json.loads(row['prediction_json']) == payload
        assert row['prediction_error_json'] is None
        assert len(calls) == 2
    finally:
        core.close()


def test_prediction_joins_atomic_experience_and_does_not_backfill(home):
    m = Memory(home/'memory.sqlite3')
    kwargs = dict(state_before=BEFORE, action='observe',state_after=AFTER,outcome={},
                  legacy_reward=.45,started_at=1000,completed_at=1002)
    try:
        old_episode, old_transition = m.record_transition_experience(**kwargs)
        payload = {'model':'transition_delta_v1','model_version':1,
                   'horizon':'next_post_action_observation','action':'observe','signals':{}}
        m.db.execute("""CREATE TRIGGER fail_prediction BEFORE INSERT ON transitions
                     WHEN NEW.prediction_json IS NOT NULL
                     BEGIN SELECT RAISE(ABORT,'injected failure'); END""")
        with pytest.raises(sqlite3.IntegrityError,match='injected failure'):
            m.record_transition_experience(**kwargs,prediction=payload)
        assert m.db.execute('SELECT count(*) FROM episodes').fetchone()[0] == 1
        assert m.db.execute('SELECT count(*) FROM transitions').fetchone()[0] == 1
        m.db.execute('DROP TRIGGER fail_prediction')
        _, new_transition = m.record_transition_experience(**kwargs,prediction=payload)
    finally:
        m.close()
    core = SeedOrganism(home)
    try:
        rows = core.memory.db.execute('SELECT id,prediction_json,prediction_error_json FROM transitions ORDER BY id').fetchall()
        assert [r[0] for r in rows] == [old_transition,new_transition]
        assert rows[0][1] is None and json.loads(rows[1][1]) == payload
        assert all(r[2] is None for r in rows)
        assert core.memory.db.execute('SELECT version FROM seed_schema').fetchone()[0] == 2
    finally:
        core.close()
