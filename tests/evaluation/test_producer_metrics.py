"""Literal and adversarial source fixtures, never registered experiments."""
import copy
import json
import threading
import pytest

from development.evaluation.contracts import CompletedEvidence
from development.evaluation.metrics.producers import measure_producers
from development.evaluation.metrics.registry import measurement_data
from .test_analysis import ClosedRoot


def plan(tmp_path, plan_body, *, frozen=False):
    from development.evaluation.analysis import validate_plan, freeze_plan
    from development.evaluation.registry import METRICS, REGISTRIES
    body = copy.deepcopy(plan_body)
    body['metrics'] = [{'id':m,'version':REGISTRIES['metric'][m]} for m in METRICS]
    body['populations'][0]['signal'] = 'all'
    body['members'][0]['measured'] = 128
    body['windows'][0]['end'] = 128
    if frozen:
        body['members'][0].update(protocol='FROZEN_SELECTION_ASSAY', training=128)
        body['populations'][0]['phase'] = 'probe'
    return freeze_plan(validate_plan(body), ClosedRoot(tmp_path))


def results(frozen_plan, tables=None, **source):
    bundle = {'tables': tables or {}, **source}
    return {m.metric:m for m in measure_producers((),{'member-0':bundle},frozen_plan)}


@pytest.mark.parametrize('action,variant,expected',[
    ('all',None,[1,0,1]),('rest',None,[None,0,None]),
    ('all','fresh',[1,0,1]),('all','stale',[0,0,0]),
])
def test_skipped_attempts_follow_registered_scope(tmp_path,plan_body,action,variant,expected):
    from development.evaluation.analysis import freeze_plan,validate_plan
    body=copy.deepcopy(plan_body)
    body['metrics']=[dict(id='decision.skipped-fallback',version=1)]
    body['questions'][0]['metrics']=['decision.skipped-fallback']
    body['members'][0]['measured']=400
    body['windows']=[dict(id=n,start=a,end=b,unit='ordinal') for n,a,b in
        [('early',1,40),('late',361,400),('whole',1,400)]]
    body['populations'][0].update(action=action,signal='all')
    if variant is not None:body['populations'][0]['variant']=variant
    frozen=freeze_plan(validate_plan(body),ClosedRoot(tmp_path))
    skipped=[dict(key=[phase,'fresh' if variant else 'default',ordinal,'pre'],attempt=n+1,status='skipped',reason='stale_decision',retry_delay_seconds=60.)
        for n,(phase,ordinal) in enumerate([('training',1),('measured',2)])]
    source={'skipped_attempts':skipped,'variants':{v:{'skipped_attempts':skipped} for v in ('fresh','stale')}}
    out=measure_producers((),{'member-0':source},frozen)
    for row in out:
        window=json.loads(row.body)['dimensions']['window']
        count=expected[['early','late','whole'].index(window)]
        if count is None:
            assert row.state=='UNAVAILABLE' and row.reason=='MISSING_SKIPPED_ACTION_SOURCE'
        else:
            assert row.value['skipped_attempts']==count
            assert row.value['attempt_inventory_count']==2
            assert row.value['excluded_attempt_count']==2-count
    assert source['skipped_attempts']==skipped


def test_skipped_attempts_without_event_scope_are_unavailable(tmp_path,plan_body):
    body=copy.deepcopy(plan_body)
    from development.evaluation.analysis import freeze_plan,validate_plan
    body['metrics']=[dict(id='decision.skipped-fallback',version=1)]
    body['questions'][0]['metrics']=['decision.skipped-fallback']
    body['populations'][0]['signal']='all'
    frozen=freeze_plan(validate_plan(body),ClosedRoot(tmp_path))
    out=measure_producers((),{'member-0':{'skipped_attempts':[{'reason':'stale_decision'}]}},frozen)
    assert out[0].state=='UNAVAILABLE' and out[0].reason=='MISSING_SKIPPED_SCOPE_SOURCE'


@pytest.mark.parametrize('q,mean,contradictions',[(20,-.025,20),(40,0.,23),(60,.0125,23)])
def test_world_lifetime_and_contradictions(tmp_path, plan_body, q, mean, contradictions):
    from seed.memory import Memory
    from seed.world_model import WorldModel
    p = tmp_path/'plan'; p.mkdir()
    frozen_plan = plan(p,plan_body)
    memory = Memory(tmp_path/'memory.sqlite3')
    try:
        world = WorldModel(memory)
        snapshots = []
        for ordinal in range(1,21+q):
            before = {'load_ratio':.5}
            after = {'load_ratio':.4 if ordinal<=20 else .55}
            _, tid = memory.record_transition_experience(state_before=before,action='rest',state_after=after,
                outcome={},legacy_reward=0,started_at=ordinal-1,completed_at=ordinal,world_model_eligible=True)
            world.observe_transition(tid)
            snapshots.append(dict(ordinal=ordinal,beliefs=[dict(r) for r in memory.db.execute('SELECT * FROM world_beliefs')]))
        tables = {'world_beliefs':[dict(r) for r in memory.db.execute('SELECT * FROM world_beliefs')], 'world_pending':[]}
        before = list(memory.db.iterdump())
        out = results(frozen_plan,tables,world_revisions=snapshots)
        counts = out['world.evidence-count'].value['beliefs']
        assert counts['1:load_ratio:action:rest:numeric_delta'] == 20+q
        audited = out['world.contradictions'].value['beliefs']['1:load_ratio:action:rest:numeric_delta']
        assert audited['count'] == contradictions
        assert audited['mean_delta'] == pytest.approx(mean)
        assert audited['confidence_reference'] == pytest.approx(.95*(1-contradictions/(20+q)))
        assert audited['confidence_matches'] is True
        assert out['world.first-belief'].value['first_publication_ordinal'] == 2
        assert list(memory.db.iterdump()) == before
    finally: memory.close()


def test_curiosity_literal_and_missing(tmp_path, plan_body):
    from seed.curiosity import assess_curiosity
    from tests.test_curiosity import error, prior
    producer = assess_curiosity(error(.2),{'battery_pct':50},'observe',{'battery_pct':51},{})
    p = prior(confidence=0)
    settled = assess_curiosity(error(.2),{'battery_pct':50},'observe',{'battery_pct':51},{'battery_pct':p})
    assert producer['score'] == .2 and settled['score'] == .1
    assessments = [dict(transition_id=n, **a) for n,a in enumerate((producer,settled),1)]
    frozen_plan = plan(tmp_path,plan_body)
    out = results(frozen_plan,{'curiosity_assessments':assessments})
    assert out['curiosity.components'].value['formula_matches'] == 2
    assert out['curiosity.bounds'].value['violations'] == 0
    missing = results(frozen_plan)
    assert missing['curiosity.components'].state == 'UNAVAILABLE'
    assert missing['curiosity.components'].value is None
    from tests.test_prediction_error import payload, predicted
    from seed.prediction_error import evaluate_prediction
    prediction = payload({'battery_pct':predicted(80),'load_ratio':predicted(.4),
                          'disk_free_pct':predicted(50),'network_reachable':predicted(True)})
    evaluation = evaluate_prediction(prediction, {'battery_pct':80,'load_ratio':.55,'disk_free_pct':50,'network':True}).to_dict()
    assert evaluation['aggregate']['mean_normalized_error'] == pytest.approx(.0375)
    shifted = assess_curiosity(evaluation,{'battery_pct':80,'load_ratio':.5,'disk_free_pct':50,'network':False},
        'rest',{'battery_pct':80,'load_ratio':.55,'disk_free_pct':50,'network':True},{})
    assert shifted['prediction_surprise'] == pytest.approx(.0375)


def test_semantic_opportunities_and_provenance(tmp_path, plan_body, monkeypatch):
    from seed.memory import Memory
    from seed.world_model import WorldModel
    from seed.semantic_memory import Consolidator
    p = tmp_path/'plan'; p.mkdir()
    frozen_plan = plan(p,plan_body)
    memory = Memory(tmp_path/'memory.sqlite3')
    try:
        import seed.world_model as world_module
        from types import SimpleNamespace
        monkeypatch.setattr(world_module,'time',SimpleNamespace(time=lambda:8.))
        for ordinal in range(1,9):
            _,tid=memory.record_transition_experience(state_before={'load_ratio':.5}, action='rest',
                state_after={'load_ratio':.4},outcome={},legacy_reward=0,started_at=ordinal-1,completed_at=ordinal,world_model_eligible=True)
            WorldModel(memory).observe_transition(tid)
        run = Consolidator(memory,clock=lambda:9).run({'load_ratio':.5,'battery_pct':80,'charging':False,'disk_free_pct':50},provenance='owner_requested')
        tables = {t:[dict(r) for r in memory.db.execute('SELECT * FROM '+t)] for t in
            ('world_beliefs','semantic_memories','semantic_memory_history','consolidation_runs','consolidation_state')}
        out = results(frozen_plan,tables)
        assert out['semantic.source-consistency'].value['matched'] == 2
        assert out['semantic.source-consistency'].value['content_matched'] == 2
        assert out['semantic.provenance'].value['valid_source_links'] == 2
        original_dump=list(memory.db.iterdump())
        wrong=copy.deepcopy(tables)
        wrong['semantic_memories'][0].update(evidence_count=999,confidence=.95,
            contradiction_count=999,payload_json='{"mean_delta":42}')
        audited=results(frozen_plan,wrong)['semantic.source-consistency'].value
        assert audited['matched']==2  # fingerprint alone is unchanged
        assert audited['content_mismatched']==1 and audited['content_matched']==1
        fact=audited['facts'][0]
        assert set(fact['content_mismatched_fields'])=={'evidence_count','confidence','contradiction_count','payload_json'}
        assert fact['actual_support']==999 and fact['reference_support']==8
        assert fact['actual_confidence']==.95 and fact['reference_confidence']==.4
        assert list(memory.db.iterdump())==original_dump
        assert out['semantic.promotion-latency'].state == 'UNAVAILABLE'  # no captured eligibility history
        opportunities=[dict(run_id=run['id'],source_belief_id=b['id'],at=8.,support=b['evidence_count'],
                            confidence=b['confidence'],resource_guard=False) for b in tables['world_beliefs']]
        actual=results(frozen_plan,tables,semantic_eligibility_history=opportunities)
        assert actual['semantic.promotion-latency'].value['eligible_opportunities']==2
        assert [e['latency'] for e in actual['semantic.promotion-latency'].value['promotions']]==[1.,1.]
        fake=copy.deepcopy(opportunities)
        for event in fake:event['run_id']=999999
        rejected=results(frozen_plan,tables,semantic_eligibility_history=fake)
        assert rejected['semantic.promotion-latency'].reason=='NO_ELIGIBLE_CONSOLIDATION_OPPORTUNITY'
        absent = results(frozen_plan,{'semantic_memories':[],'consolidation_runs':[]})
        assert absent['semantic.promotion-latency'].reason == 'NO_CONSOLIDATION_OPPORTUNITY'
        frozen_path = tmp_path/'frozen'; frozen_path.mkdir()
        readonly = results(plan(frozen_path,plan_body,frozen=True),tables)
        assert readonly['semantic.promotion-latency'].state == 'NOT_EVALUATED'
        assert readonly['semantic.revisions'].state == 'NOT_EVALUATED'
        # A real later B4 publication can precede semantic consolidation.
        _,tid=memory.record_transition_experience(state_before={'load_ratio':.5},action='rest',
            state_after={'load_ratio':.6},outcome={},legacy_reward=0,started_at=9,completed_at=10,world_model_eligible=True)
        WorldModel(memory).observe_transition(tid)
        lagged=copy.deepcopy(tables)
        lagged['world_beliefs']=[dict(r) for r in memory.db.execute('SELECT * FROM world_beliefs')]
        no_history=results(frozen_plan,lagged)['semantic.source-consistency'].value
        assert no_history['matched']==0 and no_history['content_unavailable']==2
        history=[dict(ordinal=8,beliefs=tables['world_beliefs'])]
        historical=results(frozen_plan,lagged,world_revisions=history)['semantic.source-consistency'].value
        assert historical['content_matched']==2 and historical['content_mismatched']==0
        assert all(f['content_source_version']=='historical' for f in historical['facts'])
        clock_only=copy.deepcopy(tables)
        for belief in clock_only['world_beliefs']:belief['updated_at']+=100
        assert results(frozen_plan,clock_only)['semantic.source-consistency'].value['content_matched']==2
        invalid=copy.deepcopy(tables)
        for belief in invalid['world_beliefs']:belief['value_json']='{"mean_delta":42}'
        for row in invalid['semantic_memories']:row['status']='source_unavailable'
        unavailable=results(frozen_plan,invalid)['semantic.source-consistency'].value
        assert unavailable['content_unavailable']==2
        assert all(f['source_unavailable_consistent'] for f in unavailable['facts'])
    finally: memory.close()


def test_self_claims_are_source_checked(tmp_path,plan_body):
    from seed.memory import Memory
    from seed.self_model import SelfModel, _read_evidence
    from tests.test_self_model import record
    memory = Memory(tmp_path/'memory.sqlite3')
    try:
        tid=record(memory)
        source=_read_evidence(memory.db,tid)
        assert SelfModel(memory,clock=lambda:1002).update(tid,'synthetic',threading.Event()) == 'updated'
        snapshot=json.loads(memory.db.execute('SELECT data_json FROM self_model_current').fetchone()[0])
        # Source bundle is captured before publication, not recomputed at read time.
        def plain(value):
            if isinstance(value,bytes): return value.decode()
            if hasattr(value,'keys'): return {k:plain(value[k]) for k in value.keys()}
            if isinstance(value,(list,tuple)): return [plain(v) for v in value]
            return value
        source=plain(source)
        p=tmp_path/'plan'; p.mkdir(); frozen_plan=plan(p,plan_body)
        out=results(frozen_plan,self_snapshot=snapshot,self_evidence=source,read_time=1303)
        assert out['self.unsupported-claims'].value['unsupported'] == 0
        assert out['self.freshness'].value['stale'] > 0
        wrong=copy.deepcopy(snapshot)
        wrong['observations']['load_ratio']['value']=.9
        out=results(frozen_plan,self_snapshot=wrong,self_evidence=source,read_time=1303)
        assert out['self.unsupported-claims'].value['unsupported'] >= 1
        assert any(c['path']=='observations.load_ratio.value' for c in out['self.unsupported-claims'].value['claims'])
        assert wrong['observations']['load_ratio']['value'] == .9
    finally: memory.close()


def test_decision_links_q_and_guards(tmp_path,plan_body,foundation_module):
    from .test_cycle_adapter import run_cycle
    from development.evaluation.contracts import ContractError
    p=tmp_path/'plan';p.mkdir();frozen_plan=plan(p,plan_body)
    fixture_path=tmp_path/'worker';fixture_path.mkdir()
    raw,_,_=run_cycle(fixture_path,foundation_module)
    capture=raw['record']
    point=CompletedEvidence(('measured','default',1,'update'),json.dumps(capture).encode())
    out={m.metric:m for m in measure_producers((point,),{'member-0':{}},frozen_plan)}
    assert out['decision.constraints'].value['violations'] == 0
    assert out['decision.prediction-link'].value['matched'] == 1
    assert out['decision.provenance'].value['structurally_valid'] == 1
    # An adversarial literal claim that selects an ineligible action must fail
    # engineering, even when its external task utility would look favorable.
    bad=copy.deepcopy(capture)
    bad['selection']['current']['load_ratio']=.9
    bad['selection']['selected_action']='reflect'
    bad['selection']['candidates']['reflect']['eligible']=False
    with pytest.raises(ContractError):
        measure_producers((CompletedEvidence(point.key,json.dumps(bad).encode()),),{'member-0':{}},frozen_plan)


def test_missing_denominators_and_caps_are_not_totals(tmp_path,plan_body):
    out=results(plan(tmp_path,plan_body))
    assert out['self.factual-fidelity'].state == 'UNAVAILABLE'
    assert measurement_data(out['self.factual-fidelity'])['denominator'] is None
    assert out['decision.constraints'].value is None


def test_curiosity_surprise_is_checked_against_actual_b3_source(tmp_path,plan_body):
    from seed.curiosity import assess_curiosity
    from tests.test_curiosity import error
    actual = error(.2)
    assessment = dict(transition_id=1,**assess_curiosity(actual,{'battery_pct':50},'observe',{'battery_pct':51},{}))
    assessment['prediction_surprise'] = .9  # declared adversarial producer fixture
    out = results(plan(tmp_path,plan_body),{'curiosity_assessments':[assessment]},b3_by_transition={'1':actual})
    fact = out['curiosity.components'].value['facts'][0]
    assert fact['b3_source_matches'] is False
    assert fact['b3_reference_surprise'] == .2


def test_capped_self_counts_remain_at_least(tmp_path,plan_body):
    from seed.memory import Memory
    from seed.self_model import SelfModel,_read_evidence
    from tests.test_self_model import record
    memory=Memory(tmp_path/'memory.sqlite3')
    try:
        with memory.db:
            memory.db.executemany('INSERT INTO episodes(ts,event,state_json) VALUES(?,?,?)',[(1,'fixture','{}')]*1005)
        tid=record(memory)
        source=_read_evidence(memory.db,tid)
        SelfModel(memory,clock=lambda:1002).update(tid,'synthetic',threading.Event())
        snapshot=json.loads(memory.db.execute('SELECT data_json FROM self_model_current').fetchone()[0])
        def plain(v):
            if isinstance(v,bytes):return v.decode()
            if hasattr(v,'keys'):return {k:plain(v[k]) for k in v.keys()}
            if isinstance(v,(list,tuple)):return [plain(i) for i in v]
            return v
        p=tmp_path/'plan';p.mkdir()
        out=results(plan(p,plan_body),self_snapshot=snapshot,self_evidence=plain(source))
        claim=next(c for c in out['self.factual-fidelity'].value['claims'] if c['path']=='memory.storage.episode_count')
        assert claim['actual'] == {'count':1001,'relation':'at_least'}
        assert claim['supported']
        assert memory.db.execute('SELECT COUNT(*) FROM episodes').fetchone()[0] == 1006
    finally:memory.close()


def test_actual_q_update_and_curiosity_b3_link(tmp_path,plan_body,foundation_module):
    from development.evaluation.contracts import WorkerLaunch
    from development.evaluation.channel import ChannelRouter
    from development.evaluation.scenarios.stationary import StationaryScenario
    p=tmp_path/'plan';p.mkdir();frozen_plan=plan(p,plan_body)
    root=foundation_module('paths').EvaluationRoot.create(tmp_path.resolve())
    cap=root.assign_learner('f'*32,0)
    journal=foundation_module('checkpoint').ScoreJournal.create(root,'f'*32)
    worker=foundation_module('worker').WorkerHandle.start(WorkerLaunch(cap,b'{"epsilon":0.15,"alpha":0.18}',3,'f'*64),
        channel=ChannelRouter(StationaryScenario(),journal=journal))
    try:
        response=worker.request({'operation':'cycle','key':['measured','default',1,'pre']})
        assert response['status']=='completed' and response['acked']
        tid=response['updates']['b1']['transition_id']
        assert response['capture']['prior_b4'] == {}
        source={'tables':{'curiosity_assessments':[response['updates']['b5']['assessment']]},
                'b3_by_transition':{str(tid):response['capture']['b3_result']},
                'prior_world_by_transition':{str(tid):response['capture']['prior_b4']}}
        point=CompletedEvidence(('measured','default',1,'update'),json.dumps(response).encode())
        out={m.metric:m for m in measure_producers((point,),{'member-0':source},frozen_plan)}
        assert out['decision.q-compatibility'].value['matched']==1, json.dumps(out['decision.q-compatibility'].value)
        assert out['decision.q-compatibility'].value['mismatched']==0
        assert out['curiosity.components'].value['facts'][0]['b3_source_matches'] is True
        assert out['curiosity.components'].value['facts'][0]['prior_source_status'] == 'captured'
        assert all(c['matches'] for c in out['curiosity.components'].value['facts'][0]['prior_source_checks'])
        assert out['curiosity.components'].value['source_matches']==1, json.dumps(out['curiosity.components'].value)
        original_source=copy.deepcopy(source)
        # Structural arithmetic can be self-consistent while source claims lie.
        for defect in ('uncertainty-novelty','coverage','membership','sample','component-mean','false-unavailable'):
            forged=copy.deepcopy(source)
            row=forged['tables']['curiosity_assessments'][0]
            components=json.loads(row['components_json'])
            signal=next(iter(components['signals']))
            if defect=='uncertainty-novelty':
                row.update(uncertainty=0.,novelty=0.)
                for component in components['signals'].values():component.update(uncertainty=0.,novelty=0.)
            elif defect=='coverage':row['coverage']=.5
            elif defect=='membership':components['signals'].pop(signal)
            elif defect=='sample':components['signals'][signal]['sample']+=.2
            elif defect=='component-mean':row['uncertainty']=.5
            else:row.update(status='unavailable',score=None)
            if row['status']=='evaluated':
                row['score']=row['prediction_surprise']*(.5+.5*row['uncertainty'])*(.5+.5*row['novelty'])
            row['components_json']=json.dumps(components)
            audited={m.metric:m for m in measure_producers((point,),{'member-0':forged},frozen_plan)}['curiosity.components']
            assert audited.state=='MEASURED' and audited.value['source_mismatches']==1,defect
            if defect!='false-unavailable':assert audited.value['formula_matches']==1
            assert audited.value['facts'][0]['source_mismatched_fields'],defect
        missing={m.metric:m for m in measure_producers((),{'member-0':source},frozen_plan)}['curiosity.components'].value
        assert missing['source_unavailable']==1 and missing['source_matches']==0
        assert source==original_source
        wrong=copy.deepcopy(response)
        wrong['updates']['q']['after']['value']+=1
        changed=CompletedEvidence(point.key,json.dumps(wrong).encode())
        audited={m.metric:m for m in measure_producers((changed,),{'member-0':source},frozen_plan)}
        assert audited['decision.q-compatibility'].value['mismatched']==1
    finally:worker.stop();journal.close()


def test_unselected_false_guard_is_audited_and_fails_report(tmp_path,plan_body):
    from seed.memory import Memory
    from seed.predictor import Predictor
    from seed.learner import Learner
    from seed.decision import DecisionSystem
    from seed.decision_record import validate_record
    from tests.test_decision import RNG,STATE
    from development.evaluation.metrics.findings import reconcile_output,classify_questions
    from .test_reporting import fixture_measurements
    memory=Memory(tmp_path/'memory.sqlite3')
    try:
        selector=DecisionSystem(memory,Predictor(memory),Learner(memory,epsilon=1),rng=RNG(draw=0,index=1))
        selection=selector.select(selector.prepare(STATE,selected_at=100))
        record=copy.deepcopy(selection.record)
        assert record['selected_action']=='reflect'
        record['candidates']['consolidate'].update(eligible=False,constraint_reasons=['high_load'])
        record['eligible_actions'].remove('consolidate');record['selection_candidates'].remove('consolidate')
        record['choice_index']=record['selection_candidates'].index(record['selected_action'])
        validate_record(record,prediction=selection.prediction,state_before=STATE,draft=True)
        point=CompletedEvidence(('measured','default',1,'update'),json.dumps(dict(selection=record,prediction=selection.prediction,state_before=STATE)).encode())
        root=tmp_path/'plan';root.mkdir();frozen_plan=plan(root,plan_body)
        out={m.metric:m for m in measure_producers((point,),{'member-0':{}},frozen_plan)}
        audited=out['decision.eligibility']
        assert audited.value['mismatched']==1 and audited.value['checked_candidates']==4
        assert audited.value['facts'][0]['guard_checks']['consolidate']['matches'] is False
        output=tuple(audited if m.metric=='decision.eligibility' else m for m in fixture_measurements(frozen_plan))
        report=reconcile_output(frozen_plan,output,classify_questions(frozen_plan,output,'COMPLETED'))
        assert not report.passed
        assert record['candidates']['consolidate']['eligible'] is False
    finally:memory.close()


@pytest.mark.parametrize('defect',['timestamp','unavailable','error'])
def test_self_false_missing_and_source_clock_remain_in_denominator(tmp_path,plan_body,defect):
    from seed.memory import Memory
    from seed.self_model import SelfModel,_read_evidence,validate_snapshot
    from tests.test_self_model import record
    memory=Memory(tmp_path/'memory.sqlite3')
    try:
        tid=record(memory)
        def plain(v):
            if isinstance(v,bytes):return v.decode()
            if hasattr(v,'keys'):return {k:plain(v[k]) for k in v.keys()}
            if isinstance(v,(tuple,list)):return [plain(x) for x in v]
            return v
        source=plain(_read_evidence(memory.db,tid))
        SelfModel(memory,clock=lambda:1002).update(tid,'synthetic',threading.Event())
        snapshot=json.loads(memory.db.execute('SELECT data_json FROM self_model_current').fetchone()[0])
        root=tmp_path/'plan';root.mkdir();frozen_plan=plan(root,plan_body)
        original=results(frozen_plan,self_snapshot=snapshot,self_evidence=source)
        paths=[c['path'] for c in original['self.factual-fidelity'].value['claims']]
        assert len(paths)==len(set(paths))
        wrong=copy.deepcopy(snapshot)
        if defect=='timestamp':wrong['sources']['observation']['source_observed_at']=1001
        else:wrong['observations']['load_ratio'].update(value=None,status=defect,reason='not_recorded' if defect=='unavailable' else 'invalid_value')
        validate_snapshot(wrong)
        out=results(frozen_plan,self_snapshot=wrong,self_evidence=source)
        assert out['self.unsupported-claims'].value['unsupported']>=1
        assert measurement_data(out['self.factual-fidelity'])['denominator']==measurement_data(original['self.factual-fidelity'])['denominator']
        if defect=='timestamp':
            assert out['self.freshness'].value['source_faithful'] is False
            assert out['self.unsupported-claims'].value['unsupported']==1
        else:assert any(c['path']=='observations.load_ratio.status' for c in out['self.unsupported-claims'].value['claims'])
    finally:memory.close()


def test_world_stability_honors_disjoint_windows_and_belief_scope(tmp_path,plan_body):
    from seed.memory import Memory
    from seed.world_model import WorldModel
    from development.evaluation.analysis import freeze_plan,validate_plan
    memory=Memory(tmp_path/'memory.sqlite3')
    try:
        model=WorldModel(memory)
        for n in range(2):
            _,tid=memory.record_transition_experience(state_before={'load_ratio':.5},action='rest',state_after={'load_ratio':.6},outcome={},legacy_reward=0,started_at=n,completed_at=n+1,world_model_eligible=True)
            model.observe_transition(tid)
        original=dict(memory.db.execute("SELECT * FROM world_beliefs WHERE scope='action'").fetchone())
        history=[]
        for ordinal,mean in ((1,0.),(2,.1),(361,.1),(362,1.)):
            belief=copy.deepcopy(original);value=json.loads(belief['value_json']);value['mean_delta']=mean
            belief.update(value_json=json.dumps(value),source_last_transition_id=ordinal)
            history.append(dict(ordinal=ordinal,phase='measured',beliefs=[belief]))
        body=copy.deepcopy(plan_body)
        body['metrics']=[dict(id='world.stability',version=1)];body['questions'][0]['metrics']=['world.stability']
        body['members'][0]['measured']=400
        body['populations'][0].update(action='rest',signal='load_ratio')
        body['windows']=[dict(id='early',start=1,end=40,unit='ordinal'),dict(id='late',start=361,end=400,unit='ordinal')]
        root=tmp_path/'plan';root.mkdir();frozen_plan=freeze_plan(validate_plan(body),ClosedRoot(root))
        source={'tables':{'world_beliefs':[original]},'world_revisions':history}
        out=measure_producers((),{'member-0':source},frozen_plan)
        expected={'early':.1,'late':.9}
        for row in out:
            detail=measurement_data(row);window=detail['dimensions']['window']
            facts=row.value['beliefs'][original['belief_key']]
            assert facts['mean_absolute_change']==pytest.approx(expected[window]) and facts['revisions']==1
            assert detail['source_scope']=='registered_publication_window'
        assert source['world_revisions']==history
    finally:memory.close()


def test_scoped_sources_without_event_proof_are_unavailable(tmp_path,plan_body):
    from development.evaluation.analysis import freeze_plan,validate_plan
    body=copy.deepcopy(plan_body)
    body['members'][0]['measured']=400
    body['metrics']=[dict(id='curiosity.components',version=1),dict(id='semantic.revisions',version=1),dict(id='self.factual-fidelity',version=1)]
    body['questions'][0]['metrics']=[m['id'] for m in body['metrics']]
    body['populations'][0]['signal']='all'
    body['windows']=[dict(id='early',start=1,end=40,unit='ordinal')]
    frozen_plan=freeze_plan(validate_plan(body),ClosedRoot(tmp_path))
    out=measure_producers((),{'member-0':{}},frozen_plan)
    assert all(r.state=='UNAVAILABLE' and r.reason=='MISSING_REGISTERED_SCOPE_EVIDENCE' for r in out)


def test_decision_action_population_does_not_include_other_selections(tmp_path,plan_body,foundation_module):
    from .test_cycle_adapter import run_cycle
    from development.evaluation.analysis import freeze_plan,validate_plan
    body=copy.deepcopy(plan_body);body['metrics']=[dict(id='decision.constraints',version=1)]
    body['questions'][0]['metrics']=['decision.constraints'];body['populations'][0].update(action='rest',signal='all')
    frozen_plan=freeze_plan(validate_plan(body),ClosedRoot(tmp_path))
    root=tmp_path/'worker';root.mkdir();raw,_,_=run_cycle(root,foundation_module)
    assert raw['record']['selection']['selected_action']!='rest'
    point=CompletedEvidence(('measured','default',1,'update'),json.dumps(raw['record']).encode())
    row=measure_producers((point,),{'member-0':{}},frozen_plan)[0]
    assert row.state=='UNAVAILABLE' and row.value is None


def test_world_publication_history_never_mixes_training_ordinals(tmp_path,plan_body):
    from development.evaluation.analysis import freeze_plan,validate_plan
    body=copy.deepcopy(plan_body)
    body['members'][0].update(training=2,measured=2)
    body['metrics']=[dict(id='world.stability',version=1)];body['questions'][0]['metrics']=['world.stability']
    body['windows'][0]['end']=2
    row={'signal':'load_ratio','belief_key':'literal:load:rest','evidence_count':2,'source_last_transition_id':1,'value_json':'{"mean_delta":0}'}
    history=[]
    for phase,ordinal,mean,tid in (('training',1,100,1),('training',2,101,2),('measured',1,0,3),('measured',2,.1,4)):
        history.append(dict(phase=phase,ordinal=ordinal,beliefs=[dict(row,source_last_transition_id=tid,value_json=json.dumps({'mean_delta':mean}))]))
    frozen_plan=freeze_plan(validate_plan(body),ClosedRoot(tmp_path))
    source={'tables':{'world_beliefs':[row]},'world_revisions':history}
    result=measure_producers((),{'member-0':source},frozen_plan)[0]
    assert result.value['beliefs'][row['belief_key']]['mean_absolute_change']==.1


def test_completed_producer_sample_cannot_be_counted_at_two_stages(tmp_path,plan_body,foundation_module):
    from .test_cycle_adapter import run_cycle
    from development.evaluation.contracts import ContractError
    root=tmp_path/'worker';root.mkdir();raw,_,_=run_cycle(root,foundation_module)
    point=CompletedEvidence(('measured','default',1,'update'),json.dumps(raw['record']).encode())
    duplicate=CompletedEvidence(('measured','default',1,'checkpoint'),point.body)
    root=tmp_path/'plan';root.mkdir();frozen_plan=plan(root,plan_body)
    with pytest.raises(ContractError):measure_producers((point,duplicate),{'member-0':{}},frozen_plan)


@pytest.mark.parametrize('defect',['error_latest','error_older','runtime_missing','runtime_error','consolidation_value','consolidation_missing'])
def test_self_all_source_envelopes_match_original_rows(tmp_path,plan_body,defect):
    from seed.memory import Memory
    from seed.self_model import SelfModel,_read_evidence,validate_snapshot
    from seed.telemetry import Telemetry
    from seed.semantic_memory import Consolidator
    from tests.test_self_model import record,STATE
    memory=Memory(tmp_path/'memory.sqlite3')
    try:
        with memory.db:
            memory.db.executemany("INSERT INTO events(ts,category,source,message,data_json) VALUES(990,'ERROR','actual-source','fixture','{}')",[()]*(101 if defect=='error_older' else 1))
        Telemetry(memory).runtime(heartbeat=1000,last_successful_cycle=999,session_id='actual-session')
        Consolidator(memory,clock=lambda:1000).run(STATE,provenance='owner_requested')
        tid=record(memory)
        def plain(v):
            if isinstance(v,bytes):return v.decode()
            if hasattr(v,'keys'):return {k:plain(v[k]) for k in v.keys()}
            if isinstance(v,(tuple,list)):return [plain(x) for x in v]
            return v
        source=plain(_read_evidence(memory.db,tid))
        assert SelfModel(memory,clock=lambda:1002).update(tid,'synthetic',threading.Event())=='updated'
        snapshot=json.loads(memory.db.execute('SELECT data_json FROM self_model_current').fetchone()[0])
        root=tmp_path/'plan';root.mkdir();frozen_plan=plan(root,plan_body)
        original=results(frozen_plan,self_snapshot=snapshot,self_evidence=source)
        assert original['self.unsupported-claims'].value['unsupported']==0
        wrong=copy.deepcopy(snapshot)
        if defect=='error_latest':wrong['recent_failures']['value']['latest_valid_event'].update(ts=1,source='invented-source')
        elif defect=='error_older':
            # Same published 100 IDs, but actual captured row101 proves the flag.
            wrong['recent_failures']['value']['has_older_retained_errors']=False
        elif defect=='consolidation_value':wrong['memory']['latest_consolidation']['value']['started_at']=1
        else:
            name='latest_consolidation' if defect=='consolidation_missing' else 'runtime_reported'
            wrong['memory'][name].update(value=None,status='error' if defect=='runtime_error' else 'unavailable',
                reason='invalid_value' if defect=='runtime_error' else 'no_consolidation_run' if name=='latest_consolidation' else 'missing_runtime')
        validate_snapshot(wrong)
        before=copy.deepcopy((wrong,source))
        out=results(frozen_plan,self_snapshot=wrong,self_evidence=source)
        assert out['self.unsupported-claims'].value['unsupported']>=1
        assert measurement_data(out['self.factual-fidelity'])['denominator']==measurement_data(original['self.factual-fidelity'])['denominator']
        assert out['self.freshness'].value['source_faithful'] is False
        assert (wrong,source)==before
    finally:memory.close()


@pytest.mark.parametrize('defect',['candidate','before','state_link','action_link','missing_snapshot','missing_update_before'])
def test_decision_q_provenance_matches_captured_original_state(tmp_path,plan_body,foundation_module,defect):
    from development.evaluation.contracts import WorkerLaunch
    from development.evaluation.channel import ChannelRouter
    from development.evaluation.scenarios.stationary import StationaryScenario
    root=tmp_path/'plan';root.mkdir();frozen_plan=plan(root,plan_body)
    workspace=foundation_module('paths').EvaluationRoot.create(tmp_path.resolve())
    cap=workspace.assign_learner('9'*32,0)
    journal=foundation_module('checkpoint').ScoreJournal.create(workspace,'9'*32)
    worker=foundation_module('worker').WorkerHandle.start(WorkerLaunch(cap,b'{"epsilon":1,"alpha":0.18}',3,'9'*64),
        channel=ChannelRouter(StationaryScenario(),journal=journal))
    try:
        original=worker.request({'operation':'cycle','key':['measured','default',1,'pre']})
        assert original['status']=='completed' and original['acked']
        changed=copy.deepcopy(original);capture=changed['capture'];updates=changed['updates']
        action=capture['selection']['selected_action']
        assert capture['q_snapshot'][action]==updates['q']['before']
        if defect=='candidate':
            unselected=next(a for a in capture['selection']['candidates'] if a!=action)
            capture['selection']['candidates'][unselected].update(q_value=42.,visits=99,q_missing=False)
        elif defect=='before':updates['q']['before']['q_value']=42.
        elif defect=='state_link':updates['b1']['transition']['state_before_json']='{}'
        elif defect=='action_link':updates['b1']['transition']['action']=next(a for a in capture['selection']['candidates'] if a!=action)
        elif defect=='missing_snapshot':capture.pop('q_snapshot')
        elif defect=='missing_update_before':updates['q'].pop('before')
        point=CompletedEvidence(('measured','default',1,'update'),json.dumps(changed).encode())
        out={m.metric:m for m in measure_producers((point,),{'member-0':{}},frozen_plan)}
        if defect=='candidate':
            assert out['decision.provenance'].value['q_source_mismatched_candidates']==1
            assert out['decision.provenance'].value['q_source_checked_candidates']==4
        elif defect.startswith('missing'):
            assert out['decision.q-compatibility'].state=='UNAVAILABLE'
            assert measurement_data(out['decision.q-compatibility'])['missing_source_updates']==1
            if defect=='missing_snapshot':assert out['decision.provenance'].value['q_source_unavailable_candidates']==4
        else:assert out['decision.q-compatibility'].value['mismatched']==1
        assert changed!=original and original['capture']['q_snapshot'][action]==original['updates']['q']['before']
    finally:worker.stop();journal.close()
