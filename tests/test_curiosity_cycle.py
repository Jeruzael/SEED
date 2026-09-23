import json
import socket
import sqlite3
import pytest
import seed.organism as organism_module
from seed.organism import SeedOrganism
from seed.learner import state_key
from seed.world_model import WorldModel
from tests.test_curiosity_attention import row
from tests.test_world_model import record, belief

# Largest finite load gives a large B3 relative error while the actual load is calm.
BEFORE=dict(battery_pct=100,charging=True,disk_free_pct=100,load_ratio=1e300,network=False,local_hour=12)
AFTER=dict(battery_pct=20,charging=False,disk_free_pct=10,load_ratio=0,network=True,local_hour=12)


def enable(core,enabled=True):
    core.memory.db.execute('INSERT INTO settings VALUES(1,1,?)',
                           (json.dumps({'prediction_error_curiosity':enabled,'epsilon':0}),))
    core.memory.db.commit()


def deny_io(monkeypatch):
    def denied(*args,**kw): raise AssertionError('Auxiliary reflection must not use network')
    monkeypatch.setattr(socket,'create_connection',denied)
    monkeypatch.setattr(socket,'getaddrinfo',denied)
    monkeypatch.setattr(socket,'socket',denied)


def test_curiosity_setting_accepts_boolean_and_preserves_default_off():
    from seed.config import validate_settings,DEFAULTS
    assert DEFAULTS['prediction_error_curiosity'] is False
    assert validate_settings({'prediction_error_curiosity':True})['prediction_error_curiosity'] is True
    for value in (1,'true',None):
        with pytest.raises(ValueError):validate_settings({'prediction_error_curiosity':value})
    with pytest.raises(ValueError):validate_settings({'advanced_concept_inference':True})


def test_preupdate_assessment_atomic_then_model_then_auxiliary_no_extra_io(home,monkeypatch):
    deny_io(monkeypatch)
    states=iter([BEFORE,AFTER])
    perceptions=[]
    def perceive(body):
        perceptions.append(1)
        return next(states)
    monkeypatch.setattr('seed.body.Body.perceive',perceive)
    core=SeedOrganism(home)
    try:
        assert hasattr(core,'curiosity_attention'), 'B5 core must integrate guarded attention'
        enable(core)
        core.learner.epsilon=0
        core.memory.set_q(state_key(BEFORE),'observe',.7,4)
        # A single pending sample must not be mistaken for a published belief.
        WorldModel(core.memory).observe_transition(record(core.memory,BEFORE,AFTER))
        assert belief(core.memory) is None
        # Force persistence prediction by using another action for the old source and
        # fewer than two global history samples (normal predictor fallback).
        real_reflect=core.reflect
        reflected=[]
        def reflect_spy(*args,**kwargs):
            assert len(perceptions)==2
            current=core.memory.db.execute('SELECT max(id) FROM transitions').fetchone()[0]
            assessment=row(core.memory,current)
            assert assessment['reflection_claimed']==1
            assert assessment['uncertainty']==1 and assessment['novelty']==1
            assert belief(core.memory)['evidence_count']==2
            reflected.append(kwargs)
            return real_reflect(*args,**kwargs)
        monkeypatch.setattr(core,'reflect',reflect_spy)
        delay=core.cycle()
        assert delay==8 and len(perceptions)==2
        assert len(reflected)==1 and reflected[0]['provenance']=='curiosity_triggered'
        current=core.memory.db.execute('SELECT max(id) FROM transitions').fetchone()[0]
        assessment=row(core.memory,current)
        assert assessment['score']==pytest.approx(.925)
        assert assessment['level']=='VERY_HIGH' and assessment['reflection_completed']==1
        assert core.memory.get_q(state_key(BEFORE),'observe')==pytest.approx((.502,5))
        assert core.memory.db.execute('SELECT count(*) FROM transitions').fetchone()[0]==2
        assert core.memory.db.execute('SELECT count(*) FROM curiosity_assessments').fetchone()[0]==1
        assert core.memory.db.execute('SELECT count(*) FROM world_model_processed').fetchone()[0]==2
        assert all(v['prior_belief'] is None for v in json.loads(assessment['components_json'])['signals'].values())
    finally:core.close()


@pytest.mark.parametrize('enabled',[False,True])
def test_owner_setting_controls_attention_without_changing_score(home,monkeypatch,enabled):
    states=iter([BEFORE,AFTER])
    monkeypatch.setattr('seed.body.Body.perceive',lambda _:next(states))
    core=SeedOrganism(home)
    try:
        enable(core,enabled)
        core.learner.epsilon=0
        core.memory.set_q(state_key(BEFORE),'observe',.7,4)
        core.cycle()
        r=row(core.memory,1)
        assert r['score']==pytest.approx(.925)
        assert r['reflection_completed']==int(enabled)
        assert r['suppression_reason']==(None if enabled else 'disabled_by_owner')
    finally:core.close()


@pytest.mark.parametrize('action',['observe','reflect','consolidate','rest'])
def test_equal_policy_history_with_different_prior_beliefs_keeps_b2_b3_q_and_delay(tmp_path,monkeypatch,action):
    # Same source history in both runs. Published beliefs vary only by eligibility.
    runs=[]
    for learned in (False,True):
        states=iter([BEFORE,AFTER])
        monkeypatch.setattr('seed.body.Body.perceive',lambda _:next(states))
        core=SeedOrganism(tmp_path/str(learned))
        try:
            for _ in range(4):
                record(core.memory,AFTER,BEFORE,action,eligible=learned)
            core.world_model.recover()
            core.learner.epsilon=0
            core.memory.set_q(state_key(BEFORE),action,.7,4)
            delay=core.cycle()
            current=dict(core.memory.db.execute('SELECT * FROM transitions ORDER BY id DESC LIMIT 1').fetchone())
            c=row(core.memory,current['id'])
            runs.append((current['action'],current['legacy_reward'],core.memory.get_q(state_key(BEFORE),action),
                         delay,current['prediction_json'],current['prediction_error_json'],core.learner.epsilon,
                         core.learner.alpha,c['score']))
            b=belief(core.memory)
            if learned: assert b['evidence_count']==5
            else: assert belief(core.memory,pending=True)['evidence_count']==1
        finally:core.close()
    assert runs[0][:-1]==runs[1][:-1]
    assert runs[0][-1]!=runs[1][-1]


def test_reflection_provenance_owner_policy_curiosity_and_no_double_reflect(home,monkeypatch):
    states=iter([BEFORE,AFTER])
    monkeypatch.setattr('seed.body.Body.perceive',lambda _:next(states))
    core=SeedOrganism(home)
    try:
        enable(core)
        core.learner.epsilon=0
        core.memory.set_q(state_key(BEFORE),'reflect',.7,4)
        assert core.cycle()==12
        c=row(core.memory,1)
        assert c['level']=='VERY_HIGH' and c['suppression_reason']=='already_reflected'
        assert c['reflection_claimed']==0
        core.memory.db.execute("INSERT INTO commands VALUES('owner','reflect',?,0,99999999999,'pending',NULL)",(core.session_id,))
        core.memory.db.commit()
        core.process_commands()
        events=[json.loads(r[0]) for r in core.memory.db.execute("SELECT data_json FROM events WHERE category='REFLECTION'")]
        assert [e['provenance'] for e in events]==['policy_selected','owner_requested']
        assert core.memory.db.execute('SELECT count(*) FROM transitions').fetchone()[0]==1
        assert core.memory.db.execute('SELECT count(*) FROM curiosity_assessments').fetchone()[0]==1
    finally:core.close()


def test_auxiliary_failure_does_not_abort_completed_cycle_and_next_cycle_continues(home,monkeypatch):
    states=iter([BEFORE,AFTER,BEFORE,AFTER])
    monkeypatch.setattr('seed.body.Body.perceive',lambda _:next(states))
    core=SeedOrganism(home)
    try:
        enable(core)
        core.learner.epsilon=0
        core.memory.set_q(state_key(BEFORE),'observe',.7,4)
        def fail(**kwargs): raise RuntimeError('auxiliary error')
        monkeypatch.setattr(core,'reflect',fail)
        assert core.cycle()==8
        c=row(core.memory,1)
        assert c['reflection_claimed']==1 and c['failure_reason']=='RuntimeError: auxiliary error'
        assert core.cycle()==8
        assert core.memory.db.execute('SELECT count(*) FROM curiosity_assessments').fetchone()[0]==2
        assert core.memory.db.execute('SELECT count(*) FROM transitions').fetchone()[0]==2
    finally:core.close()


def test_published_belief_contradiction_uses_prior_direction_and_exact_components(home,monkeypatch):
    states=iter([BEFORE,AFTER])
    monkeypatch.setattr('seed.body.Body.perceive',lambda _:next(states))
    core=SeedOrganism(home)
    try:
        for _ in range(4):
            core.world_model.observe_transition(record(core.memory,{'battery_pct':50},{'battery_pct':51}))
        core.learner.epsilon=0
        core.memory.set_q(state_key(BEFORE),'observe',.7,4)
        assert belief(core.memory)['value']['mean_delta']==1
        core.cycle()
        parts=json.loads(row(core.memory,5)['components_json'])['signals']['battery_pct']
        assert parts['prior_belief']['value']['mean_delta']==1
        assert parts['prior_belief']['evidence_count']==4
        assert parts['uncertainty']==.8 and parts['novelty']==1 and parts['contradictory'] is True
        assert belief(core.memory)['value']['mean_delta']==pytest.approx(-15.2)
        assert belief(core.memory)['evidence_count']==5 and belief(core.memory)['contradiction_count']==1
    finally:core.close()


def test_raw_discharging_cycle_suppresses_attention_without_extra_observations(home, monkeypatch):
    from types import SimpleNamespace
    from seed import body
    from tests.test_battery_regression import sensor_boundaries, output
    deny_io(monkeypatch)
    calls = sensor_boundaries(monkeypatch, output())
    raw = iter([output('100','charging','AC Power'), output('15','discharging')])
    disks, loads, reachable = iter([100,10]), iter([1e300,0]), iter([False,True])
    def run(*args):
        calls['battery'] += 1
        return next(raw)
    def network():
        calls['network'] += 1
        return next(reachable)
    monkeypatch.setattr(body, '_run', run)
    monkeypatch.setattr(body, 'network_reachable', network)
    monkeypatch.setattr(body.shutil, 'disk_usage', lambda _: SimpleNamespace(total=100,free=next(disks)))
    monkeypatch.setattr(body.os, 'getloadavg', lambda: (next(loads),0,0))
    core = SeedOrganism(home)
    try:
        enable(core)
        core.memory.set_q(state_key(BEFORE),'observe',.7,4)
        assert core.cycle() == 8
        transition = core.memory.db.execute('SELECT * FROM transitions').fetchone()
        after = json.loads(transition['state_after_json'])
        assert (after['battery_pct'],after['charging']) == (15,False)
        assert state_key(after) == 'low|calm|ok|day'
        assessment = row(core.memory,transition['id'])
        assert assessment['score'] == pytest.approx(.9375)
        assert assessment['level'] == 'VERY_HIGH' and assessment['coverage'] == 1
        assert assessment['suppression_reason'] == 'low_battery'
        assert assessment['reflection_claimed'] == assessment['reflection_completed'] == 0
        assert calls == {'battery':2,'network':2}
        for table in ('episodes','transitions','curiosity_assessments','q_values'):
            assert core.memory.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0] == 1
        assert core.memory.get_q(state_key(BEFORE),'observe') == pytest.approx((.502,5))
        assert core.memory.db.execute("SELECT count(*) FROM events WHERE category='PERCEPTION'").fetchone()[0] == 2
        assert not core.memory.db.execute("SELECT 1 FROM events WHERE category='REFLECTION'").fetchone()
    finally:
        core.close()
