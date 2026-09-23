"""Deterministic B5 end-to-end cases with synthetic sensors and temporary homes."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from seed.organism import SeedOrganism
from seed.learner import state_key
from seed.migrations import VERSION

BEFORE=dict(battery_pct=100,charging=True,disk_free_pct=100,load_ratio=1e300,network=False,local_hour=12)
AFTER=dict(battery_pct=20,charging=False,disk_free_pct=10,load_ratio=0,network=True,local_hour=12)


def run_scenario(root):
    cases={}
    for name,after,action,enabled in [
        ('high_allowed',AFTER,'observe',True),('zero_error',BEFORE,'observe',True),
        ('high_load',{**AFTER,'load_ratio':1},'observe',True),
        ('low_battery',{**AFTER,'battery_pct':10},'observe',True),
        ('low_disk',{**AFTER,'disk_free_pct':5},'observe',True),
        ('policy_reflect',AFTER,'reflect',True),('owner_disabled',AFTER,'observe',False),
        ('partial',{'network':True},'observe',True),('unavailable',{},'observe',True)]:
        states=iter([BEFORE,after])
        perceptions=[]
        def perceive(body):
            perceptions.append(1)
            return next(states)
        with patch('seed.body.Body.perceive',perceive),patch('seed.organism.time.time',return_value=1000.):
            core=SeedOrganism(root/name)
            try:
                core.memory.db.execute('INSERT INTO settings VALUES(1,1,?)',
                    (json.dumps({'epsilon':0,'prediction_error_curiosity':enabled}),))
                core.memory.db.commit()
                core.memory.set_q(state_key(BEFORE),action,.7,4)
                delay=core.cycle()
                db=core.memory.db
                transition=dict(db.execute('SELECT * FROM transitions').fetchone())
                assessment=dict(db.execute('SELECT * FROM curiosity_assessments').fetchone())
                assessment['components']=json.loads(assessment.pop('components_json'))
                cases[name]=dict(assessment=assessment,action=transition['action'],reward=transition['legacy_reward'],
                    prediction=json.loads(transition['prediction_json']),evaluation=json.loads(transition['prediction_error_json']),
                    q_value=core.memory.get_q(state_key(BEFORE),action)[0],delay=delay,perceptions=len(perceptions),
                    transition_count=db.execute('SELECT count(*) FROM transitions').fetchone()[0],
                    assessment_count=db.execute('SELECT count(*) FROM curiosity_assessments').fetchone()[0],
                    world_processed=db.execute('SELECT count(*) FROM world_model_processed').fetchone()[0],
                    reflection_provenance=[json.loads(r[0])['provenance'] for r in db.execute(
                        "SELECT data_json FROM events WHERE category='REFLECTION' ORDER BY id")])
            finally:core.close()
    return dict(fixture='SEED 0.2 B5 deterministic computational curiosity',schema_version=VERSION,cases=cases)


if __name__=='__main__':
    with TemporaryDirectory() as folder:
        print(json.dumps(run_scenario(Path(folder).resolve()),sort_keys=True,indent=2,allow_nan=False))
