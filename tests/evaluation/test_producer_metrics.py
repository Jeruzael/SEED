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
        assert out['semantic.provenance'].value['valid_source_links'] == 2
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
        assert out['decision.q-compatibility'].value['matched']==1
        assert out['decision.q-compatibility'].value['mismatched']==0
        assert out['curiosity.components'].value['facts'][0]['b3_source_matches'] is True
        assert out['curiosity.components'].value['facts'][0]['prior_source_status'] == 'captured'
        assert all(c['matches'] for c in out['curiosity.components'].value['facts'][0]['prior_source_checks'])
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
        wrong=copy.deepcopy(snapshot)
        if defect=='timestamp':wrong['sources']['observation']['source_observed_at']=1001
        else:wrong['observations']['load_ratio'].update(value=None,status=defect,reason='not_recorded' if defect=='unavailable' else 'invalid_value')
        validate_snapshot(wrong)
        out=results(frozen_plan,self_snapshot=wrong,self_evidence=source)
        assert out['self.unsupported-claims'].value['unsupported']>=1
        assert measurement_data(out['self.factual-fidelity'])['denominator']==measurement_data(original['self.factual-fidelity'])['denominator']
        if defect=='timestamp':assert out['self.freshness'].value['source_faithful'] is False
        else:assert any(c['path']=='observations.load_ratio.status' for c in out['self.unsupported-claims'].value['claims'])
    finally:memory.close()
