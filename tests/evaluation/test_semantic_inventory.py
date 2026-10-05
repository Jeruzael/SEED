"""Actual captured opportunity inventories remain complete before population scope."""
import copy
import json
from types import SimpleNamespace

import pytest

from development.evaluation.analysis import freeze_plan,validate_plan
from development.evaluation.metrics.producers import measure_producers
from development.evaluation.metrics.registry import measurement_data
from .test_analysis import ClosedRoot
from .test_producer_metrics import semantic_creation_events


@pytest.fixture
def original_source(tmp_path,monkeypatch):
    from seed.memory import Memory
    from seed.world_model import WorldModel
    from seed.semantic_memory import Consolidator
    import seed.world_model as wm
    monkeypatch.setattr(wm,'time',SimpleNamespace(time=lambda:8.))
    memory=Memory(tmp_path/'inventory.sqlite')
    for n in range(1,9):
        _,tid=memory.record_transition_experience(state_before={'load_ratio':.5},action='rest',state_after={'load_ratio':.4},
            outcome={},legacy_reward=0,started_at=n-1,completed_at=n,world_model_eligible=True)
        WorldModel(memory).observe_transition(tid)
    def capture(suppressed=False):
        beliefs=[dict(r) for r in memory.db.execute('SELECT * FROM world_beliefs')]
        run=Consolidator(memory,clock=lambda:9.).run(dict(load_ratio=.9 if suppressed else .5,battery_pct=80,charging=False,disk_free_pct=50),provenance='owner_requested')
        source=dict(tables={t:[dict(r) for r in memory.db.execute('SELECT * FROM '+t)] for t in
            ('world_beliefs','semantic_memories','semantic_memory_history','consolidation_runs','consolidation_state')},
            semantic_eligibility_history=[dict(run_id=run['id'],source_belief_id=b['id'],at=8.,support=b['evidence_count'],confidence=b['confidence'],resource_guard=suppressed) for b in beliefs],
            semantic_opportunity_sources={str(run['id']):dict(at=8.,beliefs=beliefs)},semantic_creation_events=semantic_creation_events(memory))
        return source,run
    yield memory,capture
    memory.close()


def assay(tmp_path,plan_body,source,action='all',signal='all'):
    body=copy.deepcopy(plan_body);body['metrics']=[dict(id='semantic.promotion-latency',version=1)]
    body['questions'][0]['metrics']=['semantic.promotion-latency'];body['members'][0]['measured']=8
    body['windows'][0]['end']=8;body['populations'][0].update(action=action,signal=signal)
    tmp_path.mkdir();plan=freeze_plan(validate_plan(body),ClosedRoot(tmp_path))
    return measure_producers((),{'member-0':source},plan)[0]


@pytest.mark.parametrize('action,signal',[('all','all'),('rest','all'),('all','load_ratio'),('rest','load_ratio')])
@pytest.mark.parametrize('defect',['one_event','all_events','one_source','one_examined_id','eligible_count','examined_count'])
def test_missing_actual_semantic_source_cannot_shrink_complete_inventory(tmp_path,plan_body,original_source,action,signal,defect):
    memory,capture=original_source;source,run=capture();original=list(memory.db.iterdump())
    honest=assay(tmp_path/'honest',plan_body,source,action,signal)
    expected=1 if action=='rest' else 2
    assert honest.state=='MEASURED' and honest.value['eligible_opportunities']==expected
    assert len(honest.value['promotions'])==expected and run['eligible_beliefs']==2
    changed=copy.deepcopy(source)
    if defect=='one_event':changed['semantic_eligibility_history'].pop()
    elif defect=='all_events':changed['semantic_eligibility_history']=[]
    elif defect=='one_source':changed['semantic_opportunity_sources'][str(run['id'])]['beliefs'].pop()
    elif defect=='one_examined_id':
        result=json.loads(changed['tables']['consolidation_runs'][0]['result_json']);result['examined_ids'].pop()
        changed['tables']['consolidation_runs'][0]['result_json']=json.dumps(result)
    elif defect=='eligible_count':changed['tables']['consolidation_runs'][0]['eligible_beliefs']=1
    else:changed['tables']['consolidation_runs'][0]['source_beliefs_examined']=1
    bad=assay(tmp_path/'changed',plan_body,changed,action,signal)
    assert bad.state=='UNAVAILABLE' and bad.value is None
    assert bad.reason in ('INCONSISTENT_CONSOLIDATION_OPPORTUNITY_INVENTORY','MISSING_OPPORTUNITY_SOURCE_VERSION')
    assert list(memory.db.iterdump())==original


@pytest.mark.parametrize('action,signal,excluded',[('all','all',2),('rest','all',1),('all','load_ratio',2),('rest','load_ratio',1)])
def test_scoped_suppressed_sources_keep_negative_opportunity_evidence(tmp_path,plan_body,original_source,action,signal,excluded):
    memory,capture=original_source;source,run=capture(True);original=list(memory.db.iterdump())
    assert run['status']=='suppressed' and run['eligible_beliefs']==0 and source['tables']['semantic_memories']==[]
    row=assay(tmp_path/'suppressed',plan_body,source,action,signal)
    assert row.state=='UNAVAILABLE' and row.reason=='NO_ELIGIBLE_CONSOLIDATION_OPPORTUNITY'
    data=measurement_data(row)
    assert data['exclusions']['not_an_actual_eligible_opportunity']==excluded
    assert data['opportunity_inventory_count']==2 and data['scoped_opportunity_count']==excluded
    assert data['scope_exclusion_count']==2-excluded
    assert list(memory.db.iterdump())==original
