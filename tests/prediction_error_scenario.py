"""Deterministic B3 fixture; all sensing/time/randomness replaced, temporary homes only.

Run: .venv/bin/python -m tests.prediction_error_scenario
Metrics here describe this three-case fixture, not a production rolling API.
"""
import json
import math
import tempfile
from pathlib import Path
from unittest.mock import patch
from seed.organism import SeedOrganism
from seed.learner import state_key

CURRENT={'battery_pct':74,'charging':True,'load_ratio':.2,'disk_free_pct':50,
         'network':False,'wall_time':1000,'local_hour':12,'load_5m_ratio':.2,
         'hostname':'synthetic','machine':'synthetic','macos':'synthetic'}
ACTUALS={'full':{**CURRENT,'battery_pct':71,'load_ratio':.6,'disk_free_pct':48,'network':False},
         'partial':{'battery_pct':73}, 'unavailable':{'battery_pct':None,'network':None}}


def _mean(values):
    return math.fsum(value/len(values) for value in values) if values else None


def _metrics(cases):
    evaluations=[case['evaluation'] for case in cases.values()]
    aggregates=[e['aggregate'] for e in evaluations]
    scored=[a for a in aggregates if a['status']=='evaluated']
    numeric={}
    for name in ('battery_pct','load_ratio','disk_free_pct'):
        errors=[e['signals'][name]['absolute_error'] for e in evaluations
                if e['signals'][name]['status']=='evaluated']
        numeric[name]={'samples':len(errors),'value':_mean(errors)}
    network=[e['signals']['network_reachable'] for e in evaluations
             if e['signals']['network_reachable']['status']=='evaluated']
    briers=[s['brier_error'] for s in network if 'brier_error' in s]
    return {'transitions':len(cases),'scored_transitions':len(scored),
            'mean_coverage':_mean([a['coverage'] for a in aggregates]),
            'mean_normalized_error':_mean([a['mean_normalized_error'] for a in scored]),
            'mean_accuracy_score':_mean([a['accuracy_score'] for a in scored]),
            'numeric_mae':numeric,
            'network_classification_accuracy':{'samples':len(network),'value':_mean([int(s['correct']) for s in network])},
            'network_mean_brier_error':{'samples':len(briers),'value':_mean(briers)}}


def run_scenario(root: Path):
    cases={}
    for label,actual in ACTUALS.items():
        observations=iter([dict(CURRENT),dict(actual)])
        with patch('seed.body.Body.perceive',side_effect=lambda:next(observations)) as sensing, \
             patch('seed.organism.time.time',return_value=1000), \
             patch('seed.learner.random.random',return_value=.5), \
             patch('seed.learner.random.choice',side_effect=lambda choices:choices[0]):
            core=SeedOrganism(root/label)
            try:
                core.learner.epsilon=0
                core.memory.set_q(state_key(CURRENT),'observe',.7,4)
                for battery,load,disk,network in [(80,.2,50,True),(70,.4,40,False)]:
                    core.memory.record_transition_experience(
                        state_before={**CURRENT,'battery_pct':battery,'load_ratio':load,'disk_free_pct':disk},
                        action='observe',state_after={**CURRENT,'battery_pct':battery-1,'load_ratio':load+.2,
                                                      'disk_free_pct':disk-1,'network':network},
                        outcome={},legacy_reward=.45,started_at=900,completed_at=901)
                old=[tuple(row) for row in core.memory.db.execute('SELECT * FROM transitions ORDER BY id')]
                with patch.object(core.predictor,'predict_candidates',wraps=core.predictor.predict_candidates) as prediction:
                    delay=core.cycle().delay_seconds
                row=core.memory.db.execute('SELECT * FROM transitions ORDER BY id DESC LIMIT 1').fetchone()
                q,visits=core.memory.get_q(state_key(CURRENT),'observe')
                cases[label]={'prediction':json.loads(row['prediction_json']),
                              'evaluation':json.loads(row['prediction_error_json']),
                              'actual':actual,'delay':delay,'q_value':q,'q_visits':visits,
                              'perceptions':sensing.call_count,'prediction_calls':prediction.call_count,
                              'schema_version':core.memory.db.execute('SELECT version FROM seed_schema').fetchone()[0],
                              'historical_errors_unchanged':old==[tuple(r) for r in core.memory.db.execute('SELECT * FROM transitions ORDER BY id LIMIT 2')]}
            finally:core.close()
    return {'fixture':'SEED 0.2 B3 deterministic evaluation','cases':cases,'metrics':_metrics(cases)}


def main():
    with tempfile.TemporaryDirectory(prefix='seed-b3-') as directory:
        result=run_scenario(Path(directory).resolve())
    print(json.dumps(result,indent=2,sort_keys=True,allow_nan=False))


if __name__=='__main__':
    main()
