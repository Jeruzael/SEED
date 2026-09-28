import json
import sqlite3
import pytest
import seed.organism as organism_module
from seed.organism import SeedOrganism
from seed.memory import Memory
from seed.learner import state_key
from seed.prediction_error import evaluate_prediction
from tests.test_transition_cycle import BEFORE, AFTER
from tests.test_prediction_error import payload, predicted


def test_error_order_original_prediction_once_and_exact_persistence(home,monkeypatch):
    trace,observations,predictions,evaluations=[],[],[],[]
    states=iter([BEFORE,AFTER])
    def perceive(_body):
        result=dict(next(states))
        trace.append('before' if not observations else 'after')
        observations.append(result)
        return result
    monkeypatch.setattr('seed.body.Body.perceive',perceive)
    core=SeedOrganism(home)
    try:
        core.learner.epsilon=0
        core.memory.set_q(state_key(BEFORE),'reflect',.7,4)
        choose,predict,act=core.decisions.select,core.predictor.predict_candidates,core.perform_action
        outcome,reward,update=organism_module.describe_outcome,core.learner.reward,core.learner.update
        persist=core.memory.record_transition_experience
        def choose_spy(state):
            trace.append('decision');return choose(state)
        def predict_spy(state,actions,*,snapshot):
            trace.append('prediction')
            assert len(observations)==1
            result=predict(state,actions,snapshot=snapshot)
            predictions.append(result.predictions['reflect'])
            return result
        def act_spy(action, state=None):
            trace.append('action');return act(action, state=state)
        def outcome_spy(before,after):
            trace.append('outcome');return outcome(before,after)
        def error_spy(prediction,actual):
            trace.append('prediction_error')
            assert len(observations)==2 and prediction==predictions[0] and actual==AFTER
            result=evaluate_prediction(prediction,actual)
            evaluations.append(result.to_dict())
            return result
        def reward_spy(state,action):
            trace.append('reward');return reward(state,action)
        def update_spy(decision,value):
            trace.append('update');return update(decision,value)
        def persist_spy(**kwargs):
            trace.append('persistence');return persist(**kwargs)
        monkeypatch.setattr(core.decisions,'select',choose_spy)
        monkeypatch.setattr(core.predictor,'predict_candidates',predict_spy)
        monkeypatch.setattr(core,'perform_action',act_spy)
        monkeypatch.setattr(organism_module,'describe_outcome',outcome_spy)
        monkeypatch.setattr(organism_module,'evaluate_prediction',error_spy,raising=False)
        monkeypatch.setattr(core.learner,'reward',reward_spy)
        monkeypatch.setattr(core.learner,'update',update_spy)
        monkeypatch.setattr(core.memory,'record_transition_experience',persist_spy)
        assert core.cycle().delay_seconds==12
        assert trace==['before','prediction','decision','reward','action','after','outcome','prediction_error','reward','update','persistence']
        assert len(predictions)==1 and len(evaluations)==1 and len(observations)==2
        row=core.memory.db.execute('SELECT * FROM transitions').fetchone()
        assert json.loads(row['prediction_json'])==predictions[0]
        evaluation=json.loads(row['prediction_error_json'])
        assert evaluation==evaluations[0]
        assert evaluation['signals']['battery_pct']['signed_error']==-70
        assert evaluation['signals']['load_ratio']['signed_error']==pytest.approx(.9)
        events=[(r[0],json.loads(r[1])) for r in core.memory.db.execute('SELECT category,data_json FROM events ORDER BY id')]
        assert [r[0] for r in events]==['PERCEPTION','DECISION','PREDICTION','ACTION','REFLECTION','ACTION','PERCEPTION','PREDICTION_ERROR','CURIOSITY','LEARNING','MEMORY','SELF_MODEL']
        assert events[7][1]==evaluation
        assert core.memory.db.execute('SELECT id FROM episodes').fetchone()[0]==row['episode_id']
    finally:core.close()


@pytest.mark.parametrize('action,reward,delay',[('observe',.45,8),('reflect',.45,12),('consolidate',0,20),('rest',0,35)])
def test_different_prediction_errors_leave_policy_reward_and_delay_identical(tmp_path,monkeypatch,action,reward,delay):
    runs=[]
    for label,after in [('exact',BEFORE),('different',AFTER)]:
        states=iter([dict(BEFORE),dict(after)])
        monkeypatch.setattr('seed.body.Body.perceive',lambda self:next(states))
        core=SeedOrganism(tmp_path/label)
        try:
            core.learner.epsilon=0
            core.memory.set_q(state_key(BEFORE),action,.7,4)
            returned=core.cycle().delay_seconds
            row=core.memory.db.execute('SELECT * FROM transitions').fetchone()
            evaluation=json.loads(row['prediction_error_json'])
            runtime=json.loads(core.memory.db.execute('SELECT data_json FROM runtime').fetchone()[0])
            runs.append((row['action'],row['legacy_reward'],core.memory.get_q(state_key(BEFORE),action),
                         returned,runtime['last_decision'],evaluation['aggregate']['mean_normalized_error']))
            assert row['legacy_reward']==reward and returned==delay
            assert core.memory.get_q(state_key(BEFORE),action)==pytest.approx((.7+.18*(reward-.7),5))
        finally:core.close()
    assert runs[0][:-1]==runs[1][:-1]
    assert runs[0][-1]==0 and runs[1][-1]>0


def test_evaluation_pair_rollback_and_historical_b1_b2_integrity(home):
    m=Memory(home/'memory.sqlite3')
    kwargs=dict(state_before=BEFORE,action='observe',state_after=AFTER,outcome={},legacy_reward=.45,started_at=1,completed_at=2)
    prediction=payload({'battery_pct':predicted(80)})
    evaluation=evaluate_prediction(prediction,AFTER).to_dict()
    try:
        m.record_transition_experience(**kwargs)  # B1
        m.record_transition_experience(**kwargs,prediction=prediction)  # B2
        old=[tuple(r) for r in m.db.execute('SELECT * FROM transitions ORDER BY id')]
        m.db.execute("""CREATE TRIGGER fail_error BEFORE INSERT ON transitions
            WHEN NEW.prediction_error_json IS NOT NULL
            BEGIN SELECT RAISE(ABORT,'evaluation insert failed'); END""")
        with pytest.raises(sqlite3.IntegrityError,match='evaluation insert failed'):
            m.record_transition_experience(**kwargs,prediction=prediction,prediction_error=evaluation)
        assert m.db.execute('SELECT count(*) FROM episodes').fetchone()[0]==2
        assert [tuple(r) for r in m.db.execute('SELECT * FROM transitions ORDER BY id')]==old
        m.db.execute('DROP TRIGGER fail_error')
        m.record_transition_experience(**kwargs,prediction=prediction,prediction_error=evaluation)
    finally:m.close()
    core=SeedOrganism(home)
    try:
        rows=core.memory.db.execute('SELECT * FROM transitions ORDER BY id').fetchall()
        assert [tuple(r) for r in rows[:2]]==old
        assert rows[0]['prediction_json'] is None and rows[0]['prediction_error_json'] is None
        assert rows[1]['prediction_json'] is not None and rows[1]['prediction_error_json'] is None
        assert json.loads(rows[2]['prediction_error_json'])==evaluation
        assert core.memory.db.execute('SELECT version FROM seed_schema').fetchone()[0]==7
    finally:core.close()
