"""Synthetic B6 revision and B5 comparison; never opens installed memory or sensors."""
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from seed.memory import Memory
from seed.world_model import WorldModel
from seed.semantic_memory import Consolidator


def run_scenario(home):
    m=Memory(home/'memory.sqlite3')
    w=WorldModel(m)
    now=[100.]
    c=Consolidator(m,clock=lambda:now[0])
    stages=[]
    def add(delta):
        tid=m.record_transition_experience(state_before={'battery_pct':max(0,-delta)},action='observe',
            state_after={'battery_pct':max(0,delta)},outcome={},legacy_reward=0,
            started_at=1,completed_at=2,world_model_eligible=True)[1]
        with patch('seed.world_model.time.time',return_value=float(tid)):w.observe_transition(tid)
    def save(name):
        run=c.run()
        memories=[]
        for row in m.db.execute('SELECT * FROM semantic_memories ORDER BY id'):
            item=dict(row)
            item['payload']=json.loads(item.pop('payload_json'))
            memories.append(item)
        stages.append(dict(name=name,run=run,memories=memories))
        now[0]+=1
    try:
        for _ in range(8):add(1)
        save('promoted')
        save('unchanged')
        for _ in range(18):
            value=json.loads(m.db.execute("SELECT value_json FROM world_beliefs WHERE scope='global'").fetchone()[0])
            add(-100 if value['mean_delta']>0 else 100)
        save('weakened')
        add(1)
        save('reactivated')
        history=[json.loads(r[0]) for r in m.db.execute(
            'SELECT record_json FROM semantic_memory_history ORDER BY semantic_memory_id,revision')]
        retained={t:m.db.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in
                  ('episodes','transitions','world_beliefs','world_model_processed','semantic_memories','semantic_memory_history')}
        return dict(fixture='SEED 0.2 B6 deterministic semantic revision',schema_version=m.db.execute('SELECT version FROM seed_schema').fetchone()[0],
                    stages=stages,history=history,retained=retained)
    finally:m.close()


def run_comparison(root):
    from tests.curiosity_scenario import run_scenario as curiosity
    from tests.world_model_scenario import run_scenario as world
    from tests.baseline_scenario import run_scenario as baseline
    from tests.prediction_error_scenario import run_scenario as evaluation
    repo=Path(__file__).parents[1]
    baseline_path=repo/'docs/baselines/seed-0.2-b5-comparison.json'
    stable=['predictor.py','prediction_error.py','learner.py','body.py','world_model.py','curiosity.py',
            'curiosity_attention.py','config.py','commands.py','runtime.py','transitions.py','telemetry.py']
    return dict(batch='B6',baseline_commit='ad83ea6',branch_base='2ddad70',
        b5_artifact_sha256=hashlib.sha256(baseline_path.read_bytes()).hexdigest(),
        command='.venv/bin/python -m tests.semantic_scenario',
        source_sha256={f:hashlib.sha256((repo/'seed'/f).read_bytes()).hexdigest() for f in stable},
        semantic_memory=run_scenario(root/'semantic'),curiosity=curiosity(root/'curiosity'),
        world_model=world(root/'world'),control=baseline(root/'control'),
        evaluation_snapshot=evaluation(root/'evaluation'))


if __name__=='__main__':
    with TemporaryDirectory() as folder:
        print(json.dumps(run_comparison(Path(folder).resolve()),indent=2,sort_keys=True,allow_nan=False))
