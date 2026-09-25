"""Deterministic B7 acceptance: synthetic evidence, fixed clocks, temporary homes."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from unittest.mock import patch
from dashboard.services.seed_service import SeedService
from seed.memory import Memory
from seed.organism import SeedOrganism
from seed.learner import state_key
from seed.self_model import SelfModel,project_snapshot
from seed.semantic_memory import Consolidator
from seed.prediction_error import evaluate_prediction
from tests.test_prediction_error import payload,predicted
from tests.test_self_model import STATE,record,current,update


def policy_run(home, enabled):
    perceptions=[]
    def perceive(_):
        perceptions.append(1)
        return dict(STATE)
    with patch('seed.body.Body.perceive',perceive),patch('seed.organism.time.time',return_value=1002):
        core=SeedOrganism(home)
        try:
            core.learner.epsilon=0
            core.memory.set_q(state_key(STATE),'observe',.7,4)
            if not enabled:core.self_model.update=lambda *args:'skipped'
            delays=[core.cycle(),core.cycle()]
            rows=[dict(r) for r in core.memory.db.execute('SELECT * FROM transitions ORDER BY id')]
            return dict(actions=[r['action'] for r in rows],rewards=[r['legacy_reward'] for r in rows],
                predictions=[json.loads(r['prediction_json']) for r in rows],
                evaluations=[json.loads(r['prediction_error_json']) for r in rows],
                q_values=[dict(r) for r in core.memory.db.execute('SELECT * FROM q_values ORDER BY state_key,action')],
                delays=delays,perceptions=len(perceptions),epsilon=core.learner.epsilon,alpha=core.learner.alpha)
        finally:core.close()


def run_scenario(root):
    home=root/'evidence'
    m=Memory(home/'memory.sqlite3')
    results=dict(fixture='SEED 0.2 B7 deterministic self-model inspection',schema_version=6)
    try:
        results['before_first_cycle']=SeedService(home,clock=lambda:1002).self_model()['reason']
        tid=record(m)
        assert update(m,tid)=='updated'
        cold=current(m)
        results['insufficient_score']=cold['prediction_performance']['score']
        forecast=payload({'battery_pct':predicted(73),'load_ratio':predicted(.4),
            'disk_free_pct':predicted(49),'network_reachable':predicted(True,probability_true=.5)})
        for actual in ({'battery_pct':71,'load_ratio':.6,'disk_free_pct':48,'network':False},{'battery_pct':73},{}):
            tid=record(m,evaluation=evaluate_prediction(forecast,actual).to_dict())
        assert update(m,tid)=='updated'
        p=current(m)
        metrics=p['prediction_performance']
        results['metrics']=dict(coverage=metrics['coverage']['value']['mean'],
            error=metrics['score']['value']['mean_normalized_error'],accuracy=metrics['score']['value']['accuracy_score'],
            samples=metrics['score']['value']['samples'],valid_evaluations=metrics['window']['value']['valid_evaluations'])
        results['fresh_resource_status']=p['observations']['network']['status']
        results['stale_resource_status']=project_snapshot(p,1063)['observations']['network']['status']
        results['stale_score_status']=project_snapshot(p,1303)['prediction_performance']['score']['status']
        with m.db:m.db.execute("INSERT INTO events(ts,category,source,message,data_json) VALUES(1001,'ERROR','synthetic','fixture','{}')")
        assert current(m)['recent_failures']['value']['count']==0
        tid=record(m,at=1003);assert update(m,tid,at=1004)=='updated'
        saved=current(m)
        results['failure_count']=saved['recent_failures']['value']['count']
        event_count=m.db.execute("SELECT count(*) FROM events WHERE category='SELF_MODEL'").fetchone()[0]
    finally:m.close()
    m=Memory(home/'memory.sqlite3')
    try:
        results['restart_payload_equal']=current(m)==saved
        results['restart_no_update']=m.db.execute("SELECT count(*) FROM events WHERE category='SELF_MODEL'").fetchone()[0]==event_count
    finally:m.close()
    with patch('seed.body.Body.perceive',return_value={**STATE,'wall_time':1004}),patch('seed.organism.time.time',return_value=1005):
        core=SeedOrganism(home)
        try:
            core.learner.epsilon=0;core.memory.set_q(state_key(STATE),'observe',.7,4)
            core.cycle()
            results['new_cycle_advances']=current(core.memory)['source_transition_id']==tid+1
            old=current(core.memory)
            core.memory.db.execute("CREATE TRIGGER fail_b7 BEFORE INSERT ON self_model_current BEGIN SELECT RAISE(ABORT,'fixture'); END")
            core.cycle()
            results['failed_write_preserves_snapshot']=current(core.memory)==old
        finally:core.close()
    m=Memory(root/'suppressed'/'memory.sqlite3')
    try:
        Consolidator(m,clock=lambda:999).run({'disk_free_pct':5},'owner_requested')
        tid=record(m,action='consolidate');assert update(m,tid)=='updated'
        p=current(m)
        results['suppressed_action_selectable']=p['capabilities']['actions']['consolidate']['value']['selectable']
        results['suppression_reason']=p['memory']['latest_consolidation']['value']['suppression_reason']
    finally:m.close()
    without=policy_run(root/'control',False)
    with_model=policy_run(root/'with-model',True)
    results['policy_equal']=without==with_model
    results['perceptions_per_run']=with_model['perceptions']
    results['policy_control']=without
    return results


if __name__=='__main__':
    with TemporaryDirectory(prefix='seed-b7-') as directory:
        print(json.dumps(run_scenario(Path(directory).resolve()),sort_keys=True,indent=2,allow_nan=False))
