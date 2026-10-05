"""Genuine technical producer outputs must retain their structured audit facts."""
import copy
import json
import threading
from dataclasses import replace
from types import SimpleNamespace

import pytest

from development.evaluation.analysis import freeze_plan, validate_plan
from development.evaluation.contracts import CompletedEvidence, Population, RunResult, RunSummary
from development.evaluation.metrics.findings import classify_questions, reconcile_output, summarize_suite
from development.evaluation.metrics.prediction import measure_prediction
from development.evaluation.metrics.producers import measure_producers
from .conftest import plan_body as body_fixture
from .test_adaptation import prechange
from .test_analysis import ClosedRoot
from .test_prediction_metrics import evidence
from .test_producer_metrics import semantic_creation_events

STRUCTURED = (
    'prediction.coverage','prediction.support-counts','prediction.adaptation-delay',
    'world.first-belief','world.evidence-count','world.contradictions','world.revision-latency',
    'world.stability','world.insufficient-evidence','curiosity.components','curiosity.bounds',
    'curiosity.unavailable','semantic.promotion-latency','semantic.revisions',
    'semantic.status-transitions','semantic.source-consistency','semantic.provenance',
    'self.factual-fidelity','self.source-traceability','self.freshness','self.unsupported-claims',
    'decision.constraints','decision.eligibility','decision.provenance','decision.prediction-link',
    'decision.skipped-fallback','decision.q-compatibility')


@pytest.fixture(scope='module')
def audit_sources(tmp_path_factory):
    from seed.memory import Memory
    from seed.world_model import WorldModel
    from seed.semantic_memory import Consolidator
    from seed.self_model import SelfModel, _read_evidence
    from tests.test_self_model import record
    import seed.world_model as world_module
    root=tmp_path_factory.mktemp('structured-source')
    memory=Memory(root/'world.sqlite');old_clock=world_module.time
    world_module.time=SimpleNamespace(time=lambda:8.)
    try:
        history=[]
        for n in range(1,10):
            _,tid=memory.record_transition_experience(state_before={'load_ratio':.5},action='rest',
                state_after={'load_ratio':.4 if n<=8 else .6},outcome={},legacy_reward=0,
                started_at=n-1,completed_at=n,world_model_eligible=True)
            WorldModel(memory).observe_transition(tid)
            beliefs=[dict(r) for r in memory.db.execute('SELECT * FROM world_beliefs')]
            history.append(dict(ordinal=n,beliefs=beliefs))
            if n==8:
                captured=copy.deepcopy(beliefs)
                run=Consolidator(memory,clock=lambda:9.).run(dict(load_ratio=.5,battery_pct=80,charging=False,disk_free_pct=50),provenance='owner_requested')
        source=dict(tables={t:[dict(r) for r in memory.db.execute('SELECT * FROM '+t)] for t in
                    ('world_beliefs','world_pending','semantic_memories','semantic_memory_history','consolidation_runs','consolidation_state')},
            world_revisions=history,first_changed_rest_ordinal=9,
            semantic_eligibility_history=[dict(run_id=run['id'],source_belief_id=b['id'],at=8.,support=b['evidence_count'],confidence=b['confidence'],resource_guard=False) for b in captured],
            semantic_opportunity_sources={str(run['id']):dict(at=8.,beliefs=captured)},
            semantic_creation_events=semantic_creation_events(memory))
    finally:memory.close();world_module.time=old_clock
    memory=Memory(root/'self.sqlite')
    def plain(v):
        if isinstance(v,bytes):return v.decode()
        if hasattr(v,'keys'):return {k:plain(v[k]) for k in v.keys()}
        if isinstance(v,(list,tuple)):return [plain(i) for i in v]
        return v
    try:
        tid=record(memory);captured=plain(_read_evidence(memory.db,tid))
        SelfModel(memory,clock=lambda:1002).update(tid,'synthetic',threading.Event())
        snapshot=json.loads(memory.db.execute('SELECT data_json FROM self_model_current').fetchone()[0])
        snapshot['observations']['load_ratio']['value']=.9  # Preserve real negative evidence.
        source.update(self_snapshot=snapshot,self_evidence=captured,read_time=1303)
    finally:memory.close()
    from development.evaluation.paths import EvaluationRoot
    from development.evaluation.checkpoint import ScoreJournal
    from development.evaluation.worker import WorkerHandle
    from development.evaluation.channel import ChannelRouter
    from development.evaluation.contracts import WorkerLaunch
    from development.evaluation.scenarios.stationary import StationaryScenario
    evaluation=EvaluationRoot.create(root.resolve());cap=evaluation.assign_learner('f'*32,0)
    journal=ScoreJournal.create(evaluation,'f'*32)
    worker=WorkerHandle.start(WorkerLaunch(cap,b'{"epsilon":0.15,"alpha":0.18}',3,'f'*64),channel=ChannelRouter(StationaryScenario(),journal=journal))
    try:
        points=[];assessments=[];b3={};prior={}
        for n in range(1,11):
            response=worker.request({'operation':'cycle','key':['measured','default',n,'pre']})
            assert response['status']=='completed' and response['acked']
            tid=response['updates']['b1']['transition_id']
            assessments.append(response['updates']['b5']['assessment'])
            b3[str(tid)]=response['capture']['b3_result'];prior[str(tid)]=response['capture']['prior_b4']
            points.append(CompletedEvidence(('measured','default',n,'update'),json.dumps(response).encode()))
        source['tables']['curiosity_assessments']=assessments
        source.update(b3_by_transition=b3,prior_world_by_transition=prior,skipped_attempts=[])
        return source,tuple(points)
    finally:worker.stop();journal.close()


def output(tmp_path,metric,sources):
    body=body_fixture.__wrapped__();family='B' if metric=='prediction.adaptation-delay' else 'A'
    count=800 if family=='B' else 400
    body['metrics']=[dict(id=metric,version=2 if family=='B' else 1)]
    body['questions'][0]['metrics']=[metric]
    body['members'][0].update(family=family,measured=count)
    body['windows'][0]['end']=count
    body['populations'][0]['signal']='load_ratio' if metric.startswith('prediction.') else 'all'
    plan=freeze_plan(validate_plan(body),ClosedRoot(tmp_path))
    if metric.startswith('prediction.'):
        rows=(prechange(),)+tuple(evidence(700+n,prediction=.55,actual=.55) for n in range(15)) if family=='B' else (evidence(1),evidence(2,prediction=None))
        row=measure_prediction(metric,rows,Population('all',('member-0',)),plan)
    else:row=measure_producers(sources[1],{'member-0':sources[0]},plan)[0]
    assert row.state=='MEASURED', (metric,row.reason)
    assert reconcile_output(plan,(row,),classify_questions(plan,(row,),'COMPLETED')).passed,metric
    return plan,row


def rejected(plan,row,value):
    data=json.loads(row.body);data['value']=value
    changed=replace(row,body=json.dumps(data).encode());rows=(changed,)
    assert not reconcile_output(plan,rows,classify_questions(plan,rows,'COMPLETED')).passed
    suite=summarize_suite(plan,(RunSummary('member-0',RunResult('COMPLETED',None)),),rows)
    assert suite['completed_valid_count']==0


@pytest.mark.parametrize('metric',STRUCTURED)
def test_empty_structured_value_cannot_be_complete_science(tmp_path,audit_sources,metric):
    plan,row=output(tmp_path,metric,audit_sources)
    rejected(plan,row,{})


MUTATIONS={
 'prediction.coverage':('seed',1.),'prediction.support-counts':('methods',{'action_mean_delta':999}),
 'prediction.adaptation-delay':('rest_exposures',0),'world.first-belief':('first_publication_ordinal',False),
 'world.evidence-count':('published',999),'world.contradictions':('beliefs',{'false':{'count':-1}}),
 'world.revision-latency':('rest_exposure_transition_latency',-1),'world.stability':('beliefs',{'false':{'mean_absolute_change':-1,'revisions':1}}),
 'world.insufficient-evidence':('published',False),'curiosity.components':('source_matches',999),
 'curiosity.bounds':('assessments',False),'curiosity.unavailable':('unavailable',999),
 'semantic.promotion-latency':('promotions',None),'semantic.revisions':('revisions',-1),
 'semantic.status-transitions':('reactivations',-1),'semantic.source-consistency':('content_matched',999),
 'semantic.provenance':('valid_source_links',999),'self.factual-fidelity':('unsupported',0),
 'self.source-traceability':('unsupported',0),'self.freshness':('stale',0),
 'self.unsupported-claims':('unsupported',0),'decision.constraints':('checked',999),
 'decision.eligibility':('matched',999),'decision.provenance':('q_source_matched_candidates',999),
 'decision.prediction-link':('matched',999),'decision.skipped-fallback':('fallback',999),
 'decision.q-compatibility':('matched',999)}


@pytest.mark.parametrize('metric',STRUCTURED)
def test_structured_counts_types_and_negative_facts_reconcile(tmp_path,audit_sources,metric):
    plan,row=output(tmp_path,metric,audit_sources)
    value=copy.deepcopy(row.value);key,wrong=MUTATIONS[metric];value[key]=wrong
    rejected(plan,row,value)


def test_semantic_report_latency_matches_original_clocks(tmp_path,audit_sources):
    plan,row=output(tmp_path,'semantic.promotion-latency',audit_sources)
    value=copy.deepcopy(row.value);value['promotions'][0]['latency']=-1.
    rejected(plan,row,value)


@pytest.mark.parametrize('metric',('curiosity.components','decision.provenance','decision.q-compatibility','self.freshness'))
def test_complete_audit_totals_cannot_be_replaced_by_first_eight_sample(tmp_path,audit_sources,metric):
    plan,row=output(tmp_path,metric,audit_sources);value=copy.deepcopy(row.value)
    if metric=='self.freshness':
        assert value['source_faithful'] is False
        value['source_faithful']=True
    else:
        assert value['fact_count']==10 and len(value['facts'])==8
        if metric=='curiosity.components':
            assert value['source_matches']==10
            value['source_matches']-=1;value['source_mismatches']+=1
        elif metric=='decision.provenance':
            value['q_source_matched_candidates']-=1;value['q_source_mismatched_candidates']+=1
        else:value['matched']-=1;value['mismatched']+=1
    rejected(plan,row,value)


@pytest.mark.parametrize('metric',('curiosity.components','semantic.promotion-latency','semantic.source-consistency','decision.eligibility','decision.q-compatibility'))
def test_primary_audit_fact_contract_rejects_invented_nested_claim(tmp_path,audit_sources,metric):
    import hashlib
    plan,row=output(tmp_path,metric,audit_sources);value=copy.deepcopy(row.value)
    value['facts'][0]['invented_inferential_claim']='favorable'
    # A self-consistent content digest is not a versioned field contract.
    if value['fact_count']<=8:
        raw=json.dumps(value['facts'],sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        value['facts_sha256']=hashlib.sha256(b'SEED_B10_AUDIT_FACTS_V1\0'+raw).hexdigest()
    rejected(plan,row,value)
