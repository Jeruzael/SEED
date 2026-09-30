"""Deterministic disposable Astra evidence. Never points at an installed home."""
import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch
from seed.memory import Memory

NOW=1700000000
CASES=('empty','predictions','models','self','decisions','boundary','legacy','legacy1','legacy2','counts','combined')


def build(destination, case='combined'):
    home=Path(destination).resolve()
    temporary=(Path(tempfile.gettempdir()).resolve(),Path('/private/tmp'))
    if case not in CASES or not any(home.is_relative_to(root) and home!=root for root in temporary):
        raise ValueError('An explicit disposable temporary destination and known case are required')
    if home.exists() and any(home.iterdir()):raise ValueError('Fixture destination must be empty')
    home.mkdir(parents=True,exist_ok=True)
    manifest={'home':str(home),'case':case,'read_at':NOW}
    if case=='legacy':
        with sqlite3.connect(home/'memory.sqlite3') as db:
            db.executescript((Path(__file__).parents[1]/'fixtures/legacy.sql').read_text())
        return manifest
    m=Memory(home/'memory.sqlite3')
    try:
        if case in ('predictions','combined'):_predictions(m,manifest)
        if case in ('models','combined'):_models(m,manifest)
        if case in ('self','combined'):_self(m,manifest)
        if case=='decisions':_decisions(m,manifest)
        if case=='boundary':
            for tid in (1,9007199254740993,2**63-1):
                with m.db:m.db.execute("INSERT OR REPLACE INTO sqlite_sequence(name,seq) VALUES('transitions',?)",(tid-1,)) if tid==1 else m.db.execute("UPDATE sqlite_sequence SET seq=? WHERE name='transitions'",(tid-1,))
                _record(m,NOW-10)
            manifest['ids']=[1,9007199254740993,2**63-1]
        if case in ('legacy1','legacy2'):
            with m.db:m.db.execute('UPDATE seed_schema SET version=?',(int(case[-1]),))
            if case=='legacy2':manifest['transition']=_record(m,NOW-10)
        if case=='counts':
            with m.db:m.db.executemany("INSERT INTO episodes(ts,event,state_json,action,reward,note) VALUES(?,'experience','{}','observe',0,'')",[(NOW,)]*1000)
        with m.db:
            m.db.execute("INSERT OR REPLACE INTO meta VALUES('identity',?)",(json.dumps(dict(name='SEED fixture',generation=0,born_at=NOW-1000)),))
            m.db.execute("INSERT OR REPLACE INTO meta VALUES('last_state',?)",(json.dumps(dict(battery_pct=80,charging=True,load_ratio=.2,disk_free_pct=50,wall_time=NOW)),))
    finally:m.close()
    return manifest


def _record(m,at,**kwargs):
    return m.record_transition_experience(state_before={},action='observe',state_after={},outcome={},legacy_reward=.25,started_at=at,completed_at=at+1,**kwargs)[1]


def _predictions(m,manifest):
    from tests.dashboard.test_predictions import prediction
    from seed.prediction_error import evaluate_prediction
    p=prediction()
    manifest['b1']=_record(m,1699999900)
    manifest['b2']=_record(m,1699999910,prediction=p)
    actual=dict(battery_pct=79,load_ratio=.75,disk_free_pct=49,network=False)
    manifest['full']=_record(m,1699999920,prediction=p,prediction_error=evaluate_prediction(p,actual).to_dict())
    manifest['partial']=_record(m,1699999930,prediction=p,prediction_error=evaluate_prediction(p,{'battery_pct':79}).to_dict())
    manifest['zero']=_record(m,1699999940,prediction=p,prediction_error=evaluate_prediction(p,dict(battery_pct=80,load_ratio=.5,disk_free_pct=50,network=True)).to_dict())
    # Brier is a probabilistic score; its genuine zero fixture needs probability1.
    zero=prediction();zero['signals']['network_reachable']['probability_true']=1
    with m.db:m.db.execute('UPDATE transitions SET prediction_json=?,prediction_error_json=? WHERE id=?',
        (json.dumps(zero),json.dumps(evaluate_prediction(zero,dict(battery_pct=80,load_ratio=.5,disk_free_pct=50,network=True)).to_dict()),manifest['zero']))


def _models(m,manifest):
    from tests.test_semantic_memory import source
    from tests.test_curiosity_attention import store
    from seed.semantic_memory import Consolidator
    belief=source(m);source(m,signal='network_reachable');manifest['belief']=belief
    engine=Consolidator(m,clock=lambda:NOW-10)
    engine.run()
    with m.db:m.db.execute('UPDATE world_beliefs SET confidence=.2')
    engine.run()
    with m.db:m.db.execute('UPDATE world_beliefs SET confidence=.4')
    engine.run();engine.run(state={'disk_free_pct':5},provenance='owner_requested')
    manifest['semantic']=m.db.execute('SELECT id FROM semantic_memories ORDER BY id LIMIT 1').fetchone()[0]
    manifest['curiosity']=store(m,score=.4,level='NOTABLE',reflection_eligible=False,suppression_reason='below_threshold')
    store(m,status='unavailable',score=None,level='UNAVAILABLE',prediction_surprise=None,uncertainty=None,novelty=None,coverage=None,reflection_eligible=False,suppression_reason='unavailable_evaluation')
    claimed=store(m,score=.6,level='HIGH')
    with m.db:m.db.execute("UPDATE curiosity_assessments SET reflection_claimed=1,claimed_at=?,failure_reason='Fixture reflection failure' WHERE transition_id=?",(NOW,claimed))


def _self(m,manifest):
    from tests.test_self_model import record,update,STATE
    observation={k:v for k,v in STATE.items() if k!='network'};observation['wall_time']=NOW-61
    tid=record(m,state=observation,at=NOW-60)
    assert update(m,tid,at=NOW)=='updated'
    manifest['self_transition']=tid


def _decisions(m,manifest):
    from tests.test_decision import STATE,RNG
    from tests.test_predictor import history
    from seed.decision import DecisionSystem
    from seed.predictor import Predictor
    from seed.learner import Learner,ACTIONS,state_key
    for action in ACTIONS:
        after={**STATE,**(dict(battery_pct=0,load_ratio=1,disk_free_pct=0) if action=='reflect' else {})}
        for _ in range(20):history(m,STATE,after,action)
        m.set_q(state_key(STATE),action,1 if action=='reflect' else 0 if action=='observe' else -1,0)
    with m.db:
        m.db.execute('UPDATE transitions SET started_at=?,completed_at=?',(1699998999,1699999000))
        m.db.execute("UPDATE sqlite_sequence SET seq=120 WHERE name='transitions'")
    system=DecisionSystem(m,Predictor(m),Learner(m,epsilon=0),rng=RNG())
    for i,at in enumerate((1699999001,1699999900,1699999910,1699999920)):
        state={**STATE,**({'disk_free_pct':5} if i>=2 else {})}
        if i:
            for action in ACTIONS:m.set_q(state_key(state),action,(100 if action=='consolidate' else 1 if action=='rest' else 0) if i>=2 else (.7 if action=='reflect' else 0),0)
        chosen=system.select(system.prepare(state,selected_at=at))
        with patch('seed.memory.time.time',return_value=at+1):
            _,tid=m.record_transition_experience(state_before=state,action=chosen.decision.action,state_after={},outcome={},legacy_reward=0,started_at=at,completed_at=at+1,prediction=chosen.prediction,decision=chosen.record)
        manifest[f'decision_{i}']=tid
    with m.db:m.db.execute("UPDATE decision_records SET data_json='broken' WHERE transition_id=124")


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('destination');parser.add_argument('--case',choices=CASES,default='combined')
    args=parser.parse_args();print(json.dumps(build(args.destination,args.case),indent=2))
