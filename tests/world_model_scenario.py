"""Synthetic B4 revision fixture; no installed memory, sensing, or network."""
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
from seed.memory import Memory
from seed.world_model import WorldModel


def run_scenario(home):
    m=Memory(home/'memory.sqlite3')
    w=WorldModel(m)
    before={'battery_pct':50,'disk_free_pct':50,'load_ratio':2,'network':True}
    try:
        for index in range(22):
            delta=1 if index<20 else -1
            after={'battery_pct':50+delta,'disk_free_pct':50+delta,'load_ratio':2+delta,'network':index<20}
            tid=m.record_transition_experience(state_before=before,action='observe',state_after=after,
                outcome={},legacy_reward=0,started_at=index,completed_at=index+.5,world_model_eligible=True)[1]
            w.observe_transition(tid)
            if index==0:
                one_sample={'beliefs':m.db.execute('SELECT count(*) FROM world_beliefs').fetchone()[0],
                            'pending':m.db.execute('SELECT count(*) FROM world_pending').fetchone()[0]}
            if index==19:
                established=m.db.execute('SELECT confidence FROM world_beliefs LIMIT 1').fetchone()[0]
        beliefs=[]
        for row in m.db.execute('SELECT * FROM world_beliefs ORDER BY belief_key'):
            item=dict(row)
            item['value']=json.loads(item.pop('value_json'))
            # Wall-clock write times are operational metadata, not deterministic metrics.
            del item['created_at'],item['updated_at'],item['id']
            beliefs.append(item)
        metrics=dict(belief_count=len(beliefs),
            beliefs_by_signal={r[0]:r[1] for r in m.db.execute('SELECT signal,count(*) FROM world_beliefs GROUP BY signal')},
            beliefs_by_scope={r[0]:r[1] for r in m.db.execute('SELECT scope,count(*) FROM world_beliefs GROUP BY scope')},
            mean_confidence=math.fsum(b['confidence'] for b in beliefs)/len(beliefs),
            processed_transitions=m.db.execute('SELECT count(*) FROM world_model_processed').fetchone()[0],
            valid_signal_samples=m.db.execute('SELECT sum(valid_signals) FROM world_model_processed').fetchone()[0],
            scoped_evidence_count=sum(b['evidence_count'] for b in beliefs),
            total_scoped_contradictions=sum(b['contradiction_count'] for b in beliefs),
            unprocessed_eligible_transitions=m.db.execute('SELECT count(*) FROM world_model_queue').fetchone()[0])
        return dict(fixture='SEED 0.2 B4 deterministic world-model revision',schema_version=3,
                    one_sample=one_sample,established_confidence=established,beliefs=beliefs,metrics=metrics)
    finally:
        m.close()


if __name__=='__main__':
    with TemporaryDirectory() as directory:
        print(json.dumps(run_scenario(Path(directory).resolve()),indent=2,sort_keys=True,allow_nan=False))
