"""Characterize the unchanged Germination learner using hand-calculated cases."""
import pytest
from seed.learner import Learner, state_key
from seed.memory import Memory

@pytest.mark.parametrize('state,expected',[
    ({},'unknown|calm|ok|day'),
    ({'charging':True},'unknown|calm|ok|day'),
    ({'battery_pct':19,'charging':False,'load_ratio':.76,'disk_free_pct':9,'local_hour':5},'low|busy|tight|night'),
    ({'battery_pct':20,'load_ratio':.75,'disk_free_pct':10,'local_hour':6},'mid|calm|ok|day'),
    ({'battery_pct':54},'mid|calm|ok|day'),
    ({'battery_pct':55},'high|calm|ok|day'),
    ({'battery_pct':1,'charging':True},'charging|calm|ok|day'),
])
def test_state_categories_at_boundaries(state,expected):
    assert state_key(state)==expected

@pytest.mark.parametrize('state,rewards',[
    ({'battery_pct':80,'charging':True,'load_ratio':.1,'disk_free_pct':75},[.45,.45,0,0]),
    ({'battery_pct':10,'charging':False,'load_ratio':1,'disk_free_pct':5},[-1.2,-1.2,-.2,2]),
    ({'battery_pct':None,'load_ratio':.1,'disk_free_pct':5},[.25,.25,.8,-.2]),
    ({'battery_pct':20,'charging':False,'load_ratio':.8,'disk_free_pct':10},[0,0,0,0]),
    ({'battery_pct':40,'charging':False,'load_ratio':.5,'disk_free_pct':75},[0,0,0,0]),
])
def test_reward_table(state,rewards):
    learner=Learner(None)
    assert [learner.reward(state,a) for a in ('observe','reflect','consolidate','rest')]==rewards

@pytest.mark.parametrize('epsilon,expected,exploration',[(0,'reflect',False),(1,'rest',True)])
def test_selection_uses_exploration_branch_not_random_luck(home,monkeypatch,epsilon,expected,exploration):
    memory=Memory(home/'memory.sqlite3')
    try:
        state={'battery_pct':80}
        memory.set_q(state_key(state),'reflect',.7,4)
        monkeypatch.setattr('seed.learner.random.random',lambda:.5)
        monkeypatch.setattr('seed.learner.random.choice',lambda candidates:candidates[-1])
        learner=Learner(memory,epsilon=epsilon)
        decision=learner.choose(state)
        assert decision.action==expected and decision.exploration is exploration
        assert decision.values['reflect']==.7 and decision.visits['reflect']==4
        learner.update(decision,.45)
        if epsilon==0:
            assert memory.get_q(state_key(state),'reflect')==pytest.approx((.655,5))
        else:
            assert memory.get_q(state_key(state),'rest')==pytest.approx((.081,1))
        assert decision.values['reflect']==.7  # selection-time snapshot survives update
    finally:memory.close()
