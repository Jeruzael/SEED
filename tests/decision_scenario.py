"""B8 deterministic synthetic acceptance; writes only caller-owned temporary homes."""
import hashlib
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from seed.memory import Memory
from seed.learner import ACTIONS, Learner, state_key
from seed.predictor import Predictor
from seed.decision import DecisionSystem
from seed.organism import SeedOrganism
from tests.test_decision import STATE, RNG
from tests.test_predictor import history

REPO=Path(__file__).parents[1]


def run_scenario(root):
    cases={}
    def selection(name,changes=None,qs=None,rows=0,delta=None,epsilon=0,index=0,clock=100.,draw=.5):
        state={**STATE,**(changes or {})}
        if state.get('disk_free_pct')=='missing':state.pop('disk_free_pct')
        m=Memory(root/name/'memory.sqlite3')
        try:
            learner=Learner(m,epsilon=epsilon)
            rng=RNG(draw,index)
            system=DecisionSystem(m,Predictor(m),learner,rng=rng)
            for a,q in (qs or {}).items():m.set_q(state_key(state),a,q,0)
            for action in ACTIONS:
                for _ in range(rows):history(m,state,{**state,**((delta or {}).get(action,{}))},action)
            picked=system.select(system.prepare(state,selected_at=clock,decision_id='0'*32))
            r=picked.record
            result={key:r[key] for key in ('selected_action','selection_mode','policy_basis','selection_candidates','choice_index','fallback_reason')}
            result.update(utilities={a:r['candidates'][a]['decision_utility'] for a in ACTIONS},
                reasons={a:r['candidates'][a]['constraint_reasons'] for a in ACTIONS},
                components=r['candidates'][r['selected_action']]['components'],
                selected_prediction_sha256=r['selected_prediction_sha256'])
            cases[name]=result
            return picked
        finally:m.close()
    selection('q_fallback',qs={'reflect':.7})
    selection('low_disk',{'disk_free_pct':5},{'consolidate':100,'rest':1})
    selection('load_battery',{'battery_pct':10,'load_ratio':.9},{'rest':1})
    selection('guard_equality',{'battery_pct':20,'load_ratio':.8,'disk_free_pct':10})
    selection('charging',{'battery_pct':10,'charging':True})
    selection('conflict',qs={'reflect':1,'rest':-1,'consolidate':-1},rows=20,
              delta={'reflect':dict(battery_pct=0,load_ratio=1,disk_free_pct=0)})
    selection('partial',{'disk_free_pct':'missing'},{'rest':-1},rows=20)
    for index in (0,1):
        selection('explore_'+str(index),{'disk_free_pct':5},{'consolidate':100},epsilon=1,index=index)
        selection('fallback_tie_'+str(index),{'disk_free_pct':5},{'consolidate':100,'observe':1,'rest':1},index=index)
    for index in (0,3):selection('composite_tie_'+str(index),rows=5,index=index)
    selection('epsilon_equality',qs={'rest':1},epsilon=.5,draw=.5)
    selection('stale_history',rows=2,clock=302.001)
    selection('fresh_history_boundary',rows=2,clock=302.)
    # Real cycle provenance, Q compatibility, owner guard and durable restart.
    with patch('seed.body.Body.perceive',return_value=dict(STATE)),patch('seed.organism.time.time',return_value=100.):
        core=SeedOrganism(root/'cycle')
        core.decisions.rng=RNG();core.learner.epsilon=0
        core.memory.set_q(state_key(STATE),'reflect',.7,4)
        result=core.cycle()
        record=core.memory.db.execute('SELECT data_json FROM decision_records').fetchone()[0]
        prediction=core.memory.db.execute('SELECT prediction_json FROM transitions').fetchone()[0]
        telemetry=core.memory.db.execute("SELECT data_json FROM events WHERE category='PREDICTION'").fetchone()[0]
        cases['completed']=dict(status=result.status,delay=result.delay_seconds,q=list(core.memory.get_q(state_key(STATE),'reflect')),
            prediction_identity=json.loads(prediction)==json.loads(telemetry),record_bytes=len(record.encode()),
            digest_matches=hashlib.sha256(json.dumps(json.loads(prediction),sort_keys=True).encode()).hexdigest()==json.loads(record)['selected_prediction_sha256'])
        core.memory.set_meta('last_state',{**STATE,'disk_free_pct':5})
        core.memory.db.execute("INSERT INTO commands VALUES('owner','consolidate',?,0,99999999999,'pending',NULL)",(core.session_id,));core.memory.db.commit()
        core.process_commands()
        run=core.memory.db.execute('SELECT status,result_json FROM consolidation_runs').fetchone()
        cases['owner_low_disk']=dict(status=run['status'],reason=json.loads(run['result_json'])['reason'],
            decision_count=core.memory.db.execute('SELECT count(*) FROM decision_records').fetchone()[0])
        core.close()
        core=SeedOrganism(root/'cycle')
        cases['restart']=dict(unchanged=core.memory.db.execute('SELECT data_json FROM decision_records').fetchone()[0]==record,
            count=core.memory.db.execute('SELECT count(*) FROM decision_records').fetchone()[0])
        core.close()
    # Stale nonfatal skip with actual core; no post-observation/downstream writes.
    for elapsed in (5.,5.001):
        now=[10.];perceptions=[]
        with patch('seed.body.Body.perceive',side_effect=lambda:perceptions.append(1) or dict(STATE)),patch('seed.organism.time.time',return_value=100.),patch('seed.organism.time.monotonic',side_effect=lambda:now[0]):
            core=SeedOrganism(root/('age_'+str(elapsed)));core.decisions.rng=RNG();core.learner.epsilon=0
            prepare=core.decisions.prepare
            def slow(*a,**kw):
                result=prepare(*a,**kw);now[0]+=elapsed;return result
            core.decisions.prepare=slow
            result=core.cycle()
            cases['age_'+str(elapsed)]=dict(status=result.status,delay=result.delay_seconds,reason=result.reason,
                perceptions=len(perceptions),decisions=core.memory.db.execute('SELECT count(*) FROM decision_records').fetchone()[0],
                q_rows=core.memory.db.execute('SELECT count(*) FROM q_values').fetchone()[0])
            core.close()
    from tests.baseline_scenario import run_scenario as baseline
    control=baseline(root/'control')
    for key in ('database_footprint','database_page_count'):control.pop(key)
    artifacts=sorted((REPO/'docs/baselines').glob('*.json'))
    return dict(batch='B8',schema_version=7,verified_master='92e6aa47ec01d80e123e1c9a90c10f9e59e367fb',
        approved_design='4c24d7ed97dd913dbe6484b23945070573145824',
        historical_artifact_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in artifacts if p.name!='seed-0.2-b8-comparison.json'},
        cases=cases,control=control)

if __name__=='__main__':
    with tempfile.TemporaryDirectory(prefix='seed-b8-') as folder:
        print(json.dumps(run_scenario(Path(folder).resolve()),sort_keys=True,indent=2,allow_nan=False))
