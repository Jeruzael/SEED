"""Preregistered output accounting fixtures, not empirical suite dispatch."""
import copy
from dataclasses import replace
import json
import pytest

from development.evaluation.analysis import default_plan,expand_inventory,freeze_plan,validate_plan
from development.evaluation.contracts import RunResult,RunSummary
from development.evaluation.metrics.findings import classify_questions,reconcile_output,summarize_suite
from development.evaluation.metrics.registry import expected_metadata
from development.evaluation.registry import METRICS
from .test_analysis import ClosedRoot


def admitted(tmp_path,body):
    return freeze_plan(validate_plan(body),ClosedRoot(tmp_path))


def fixture_measurements(plan,values=None):
    output=[]
    for row in expand_inventory(plan.plan):
        data=expected_metadata(plan,row)
        applicable=data.pop('applicable')
        if not applicable:
            state='NOT_EVALUATED';value=None
        elif values is None:
            state='UNAVAILABLE';value=None;data['reason']='INSUFFICIENT_EVIDENCE'
        else:
            value=values.get(row.member,values.get(row.metric,.5))
            state='MEASURED' if value is not None else 'UNAVAILABLE'
            data['reason']=None if value is not None else 'INSUFFICIENT_EVIDENCE'
        numeric=row.metric in ('prediction.numeric-mae','prediction.numeric-normalized-mae',
            'prediction.boolean-accuracy','prediction.boolean-brier','prediction.window-change','decision.task-utility')
        if value is not None and not numeric and type(value) is not dict:
            value={'literal_fixture':value}
        if state=='MEASURED' and row.metric.startswith('prediction.') and numeric and row.metric!='prediction.window-change':
            method=data['dimensions']['method'];comparison=data['dimensions']['comparison']
            data.update(baseline_numerator=value,baseline_value=value if comparison is not None else None,
                summary_minimum_paired=1,action_strata={'rest':dict(opportunities=1,paired=1,numerator=value,baseline_numerator=value,value=None,baseline_value=None)},
                opportunities=1,exclusions=0,eligibility_cross_tab=dict(both=1,seed_only=0,baseline_only=0,neither=0),
                reason_cross_tab={'eligible|eligible':1},coverage={m:1. for m in (method,comparison) if m is not None})
        if state=='MEASURED' and row.metric=='prediction.window-change':
            data.update(qualifying_actions=['rest'],standardized=dict(early=value+1.,late=1.),
                per_action={'rest':dict(early=value+1.,late=1.,early_count=5,late_count=5)})
        data.update(value=value,plan_digest=plan.digest,numerator=None if value is None or not numeric else value,
                    denominator=None if value is None or not numeric else 1,unit='literal_report_fixture')
        output.append(replace(row,state=state,body=json.dumps(data).encode()))
    return tuple(output)


def test_default_all_33_measurements_preregistered_and_applicable(tmp_path):
    plan=freeze_plan(default_plan(),ClosedRoot(tmp_path))
    body=json.loads(plan.plan.body)
    assert len(body['members'])==30 and body['seeds']==[0,1,2,3,4]
    inventory=expand_inventory(plan.plan)
    for member in body['members']:
        assert {r.metric for r in inventory if r.member==member['id']}==set(METRICS)
    for row in inventory:
        meta=expected_metadata(plan,row)
        assert meta['dimensions']['action_strata']==['observe','reflect','consolidate','rest']
        if row.metric=='prediction.adaptation-delay':
            assert meta['applicable']==(meta['dimensions']['family']=='B')
        if row.metric=='decision.task-utility':
            assert meta['applicable']==(meta['dimensions']['family']=='D')
    output=fixture_measurements(plan)
    findings=classify_questions(plan,output,'COMPLETED')
    report=reconcile_output(plan,output,findings)
    assert report.passed and report.status=='PASS'
    assert all(f.status=='NOT_EVALUATED' for f in findings)


@pytest.mark.parametrize('defect',['missing','duplicate','version','dimensions','unregistered','zero_missing'])
def test_bad_completed_inventory_invalidates(tmp_path,plan_body,defect):
    plan=admitted(tmp_path,plan_body);output=list(fixture_measurements(plan))
    if defect=='missing':output=[]
    elif defect=='duplicate':output*=2
    elif defect=='version':output[0]=replace(output[0],version=2)
    elif defect=='unregistered':output[0]=replace(output[0],identity='invented-primary')
    else:
        data=json.loads(output[0].body)
        if defect=='dimensions':data['dimensions']['signal']='battery_pct'
        else:data['value']=0  # unavailable never becomes zero
        output[0]=replace(output[0],body=json.dumps(data).encode())
    findings=classify_questions(plan,tuple(output),'COMPLETED')
    report=reconcile_output(plan,tuple(output),findings)
    assert not report.passed and report.status=='FAILED' and report.reason=='SCIENTIFIC_REPORT_INVALID'


def classification_body(plan_body):
    body=copy.deepcopy(plan_body)
    body['thresholds']=[dict(id='literal-tolerance',version=1,value=.2,metric='prediction.numeric-mae',metric_version=1,
        population='all',direction='le',role='classification',rationale='Literal classification contract fixture, not a SEED efficacy criterion.',missing_rule='inconclusive')]
    body['questions']=[dict(id='literal-question',metrics=['prediction.numeric-mae'],rule='thresholds_v1',
        reason='PREREGISTERED_THRESHOLD_RULE',thresholds=['literal-tolerance'])]
    return body


@pytest.mark.parametrize('value,status',[(.1,'POSITIVE'),(.3,'NEGATIVE'),(None,'INCONCLUSIVE')])
def test_execution_and_finding_states_independent(tmp_path,plan_body,value,status):
    plan=admitted(tmp_path,classification_body(plan_body))
    output=fixture_measurements(plan,{'prediction.numeric-mae':value})
    findings=classify_questions(plan,output,'COMPLETED')
    assert findings[0].status==status
    assert reconcile_output(plan,output,findings).passed
    for execution in ('FAILED','INCOMPLETE'):
        assert classify_questions(plan,output,execution)[0].status=='INCONCLUSIVE'
    assert classify_questions(plan,output,'INVALID')[0].status=='NOT_EVALUATED'


def test_mixed_and_default_descriptive_findings(tmp_path,plan_body):
    body=classification_body(plan_body)
    body['members'].append({**body['members'][0],'id':'member-1'})
    plan=admitted(tmp_path,body)
    output=fixture_measurements(plan,{'member-0':.1,'member-1':.3})
    assert classify_questions(plan,output,'COMPLETED')[0].status=='MIXED'
    second=tmp_path/'default';second.mkdir()
    descriptive=admitted(second,plan_body)
    assert classify_questions(descriptive,fixture_measurements(descriptive),'COMPLETED')[0].reason=='DESCRIPTIVE_ONLY_NO_CLASSIFICATION_RULE'


def test_exploratory_never_replaces_primary(tmp_path,plan_body):
    plan=admitted(tmp_path,plan_body)
    primary=fixture_measurements(plan)
    fake=replace(primary[0],role='EXPLORATORY_DIAGNOSTIC')
    assert not reconcile_output(plan,(fake,),classify_questions(plan,(fake,),'COMPLETED')).passed
    extra=replace(primary[0],identity=primary[0].identity+'~exploratory',role='EXPLORATORY_DIAGNOSTIC')
    assert not reconcile_output(plan,primary+(extra,),classify_questions(plan,primary,'COMPLETED')).passed


def test_suite_keeps_failed_seeds_and_incomplete_prefixes(tmp_path,plan_body):
    body=copy.deepcopy(plan_body)
    body['seeds']=[0,1,2,3]
    body['members']=[{**body['members'][0],'id':'member-'+str(n),'seed':n} for n in range(4)]
    plan=admitted(tmp_path,body)
    measurements=fixture_measurements(plan,{'member-0':.1,'member-1':.9,'member-2':.5,'member-3':.7})
    runs=tuple(RunSummary('member-'+str(n),RunResult(status,'literal-failure' if status=='FAILED' else None),
        body=json.dumps({'completed_prefix':1,'checkpoints':[1]}).encode()) for n,status in enumerate(('COMPLETED','INCOMPLETE','FAILED','INVALID')))
    result=summarize_suite(plan,runs,measurements)
    assert result['planned_count']==4 and result['completed_valid_count']==1
    assert result['incomplete_count']==1 and result['failed_count']==1 and result['invalid_count']==1
    assert len(result['members'])==4
    aggregate=result['aggregates'][0]
    assert aggregate['sample_weighted_mean']==.1 and aggregate['per_run_mean']==.1
    assert aggregate['median']==.1 and aggregate['min']==.1 and aggregate['max']==.1
    assert aggregate['complete_run_count']==1 and aggregate['incomplete_prefix_count']==1
    assert result['members'][1]['completed_prefix']==1 and result['members'][1]['checkpoints']==[1]


def test_arbitrary_classification_expression_rejected(plan_body):
    body=classification_body(plan_body)
    body['questions'][0]['rule']='eval(value<0.5)'
    with pytest.raises(ValueError):validate_plan(body)


@pytest.mark.parametrize('value,passed',[
    ({'violations':0,'assessments':1},True),
    ({'violations':1,'assessments':1},False),
    ({'assessments':1},False),
    ({'violations':False,'assessments':1},False),
    (None,True),
])
def test_curiosity_mandatory_zero_bounds_reconciliation(tmp_path,plan_body,value,passed):
    body=copy.deepcopy(plan_body)
    body['metrics']=[{'id':'curiosity.bounds','version':1}]
    body['questions'][0]['metrics']=['curiosity.bounds']
    plan=admitted(tmp_path,body)
    output=fixture_measurements(plan,{'curiosity.bounds':value})
    report=reconcile_output(plan,output,classify_questions(plan,output,'COMPLETED'))
    assert report.passed is passed
    assert output[0].value==value  # rejection never repairs the measurement


def test_forged_finding_disagrees_with_frozen_rule(tmp_path,plan_body):
    plan=admitted(tmp_path,classification_body(plan_body))
    output=fixture_measurements(plan,{'prediction.numeric-mae':.3})
    finding=classify_questions(plan,output,'COMPLETED')[0]
    assert finding.status=='NEGATIVE'
    assert not reconcile_output(plan,output,(replace(finding,status='POSITIVE'),)).passed


def test_preregistered_exploratory_is_non_inferential_and_cannot_fill_primary(tmp_path):
    plan=freeze_plan(default_plan(),ClosedRoot(tmp_path))
    output=fixture_measurements(plan)
    exploratory=[r for r in output if r.role=='EXPLORATORY_DIAGNOSTIC']
    assert exploratory and all(json.loads(r.body)['non_inferential'] is True for r in exploratory)
    assert reconcile_output(plan,output,classify_questions(plan,output,'COMPLETED')).passed
    primary=next(r for r in output if r.role=='PRIMARY' and r.metric=='prediction.numeric-mae')
    reduced=tuple(r for r in output if r.identity!=primary.identity)
    assert not reconcile_output(plan,reduced,classify_questions(plan,reduced,'COMPLETED')).passed


def test_policy_pair_requires_both_complete_and_equal_initial_state(tmp_path,plan_body):
    body=copy.deepcopy(plan_body)
    body['members']=[{**body['members'][0],'id':'d-'+role,'family':'D','scenario_version':1,'rule_version':1,'variant':role} for role in ('seed','random-eligible')]
    plan=admitted(tmp_path,body)
    output=fixture_measurements(plan,{'prediction.numeric-mae':.1})
    runs=tuple(RunSummary('d-'+role,RunResult('COMPLETED',None),json.dumps({'initial_digest':'a'*64,'completed_prefix':1,'checkpoints':[1]}).encode()) for role in ('seed','random-eligible'))
    assert summarize_suite(plan,runs,output)['paired_policy_members'][0]['eligible']
    partial=(runs[0],replace(runs[1],execution=RunResult('FAILED','literal-failure')))
    pair=summarize_suite(plan,partial,output)['paired_policy_members'][0]
    assert pair['missing_or_incomplete_members']==['random-eligible'] and not pair['eligible']
    unequal=(runs[0],replace(runs[1],body=json.dumps({'initial_digest':'b'*64}).encode()))
    assert summarize_suite(plan,unequal,output)['paired_policy_members'][0]['reason']=='UNVERIFIED_EQUAL_INITIAL_STATE'


def test_changed_standardized_population_is_not_pooled(tmp_path,plan_body):
    body=copy.deepcopy(plan_body)
    body['metrics']=[{'id':'prediction.window-change','version':1}]
    body['questions'][0]['metrics']=['prediction.window-change']
    body['members'].append({**body['members'][0],'id':'member-1'})
    plan=admitted(tmp_path,body)
    output=list(fixture_measurements(plan,{'prediction.window-change':.1}))
    for n,row in enumerate(output):
        data=json.loads(row.body);data['qualifying_actions']=['rest'] if n==0 else ['rest','reflect']
        if n==1:data['per_action']['reflect']=dict(data['per_action']['rest'])
        output[n]=replace(row,body=json.dumps(data).encode())
    runs=tuple(RunSummary('member-'+str(n),RunResult('COMPLETED',None)) for n in range(2))
    result=summarize_suite(plan,runs,tuple(output))
    assert result['aggregates'][0]['per_run_mean'] is None
    assert result['aggregates'][0]['incompatible_reason']=='CHANGED_QUALIFYING_ACTION_SET'


def test_sample_weighting_and_per_run_statistics_are_distinct(tmp_path,plan_body):
    body=copy.deepcopy(plan_body)
    body['members'].append({**body['members'][0],'id':'member-1'})
    plan=admitted(tmp_path,body)
    output=list(fixture_measurements(plan,{'member-0':.2,'member-1':.8}))
    data=json.loads(output[0].body);data.update(numerator=2,baseline_numerator=2,action_strata={'rest':dict(opportunities=10,paired=10,numerator=2,baseline_numerator=2,value=.2,baseline_value=.2)},denominator=10,opportunities=10,eligibility_cross_tab=dict(both=10,seed_only=0,baseline_only=0,neither=0),reason_cross_tab={'eligible|eligible':10})
    output[0]=replace(output[0],body=json.dumps(data).encode())
    runs=tuple(RunSummary('member-'+str(n),RunResult('COMPLETED',None)) for n in range(2))
    aggregate=summarize_suite(plan,runs,tuple(output))['aggregates'][0]
    assert aggregate['sample_weighted_mean']==pytest.approx(2.8/11)
    assert aggregate['per_run_mean']==.5 and aggregate['median']==.5
    assert aggregate['min']==.2 and aggregate['max']==.8


def test_metrics_byte_limit_rejects_oversized_report(tmp_path,plan_body):
    plan=admitted(tmp_path,plan_body)
    row=fixture_measurements(plan)[0]
    data=json.loads(row.body);data['diagnostic']=['x'*4096]*16
    report=reconcile_output(plan,(replace(row,body=json.dumps(data).encode()),),classify_questions(plan,(row,),'COMPLETED'))
    assert not report.passed


def test_long_producer_report_retains_all_audit_counts_with_bounded_detail(tmp_path,plan_body):
    from seed.curiosity import assess_curiosity
    from tests.test_curiosity import error
    from .test_producer_metrics import plan,results
    producer=assess_curiosity(error(.2),{'battery_pct':50},'observe',{'battery_pct':51},{})
    rows=[dict(transition_id=i+1,**producer) for i in range(800)]
    rows[-1]['score']=.9  # a late bad claim must survive diagnostic sampling
    report=results(plan(tmp_path,plan_body),{'curiosity_assessments':rows})['curiosity.components']
    assert report.value['assessments']==800 and report.value['formula_matches']==799
    assert report.value['fact_count']==800
    assert report.value['diagnostic_sample_non_inferential'] is True
    assert len(report.value['facts'])==8 and report.value['facts'][0]['transition_id']==1
    assert len(report.body)<16*1024


def test_suite_summary_control_bound_is_enforced(tmp_path,plan_body):
    from development.evaluation.contracts import ContractError
    plan=admitted(tmp_path,plan_body)
    output=fixture_measurements(plan)
    run=RunSummary('member-0',RunResult('FAILED','x'* (4*1024**2)))
    with pytest.raises(ContractError):summarize_suite(plan,(run,),output)


def test_equal_start_policy_utility_difference_uses_complete_runs_only(tmp_path,plan_body):
    body=copy.deepcopy(plan_body)
    body['metrics']=[dict(id='decision.task-utility',version=1)]
    body['questions'][0]['metrics']=['decision.task-utility']
    body['members']=[{**body['members'][0],'id':'d-'+role,'family':'D','scenario_version':1,'rule_version':1,'variant':role} for role in ('seed','random-eligible')]
    plan=admitted(tmp_path,body)
    output=fixture_measurements(plan,{'d-seed':.75,'d-random-eligible':.5})
    runs=tuple(RunSummary('d-'+role,RunResult('COMPLETED',None),json.dumps({'initial_digest':'a'*64}).encode()) for role in ('seed','random-eligible'))
    pair=summarize_suite(plan,runs,output)['paired_policy_members'][0]
    assert pair['utility_comparisons'][0]['seed_minus_random_eligible']==.25
    partial=(runs[0],replace(runs[1],execution=RunResult('INCOMPLETE','prefix')))
    assert summarize_suite(plan,partial,output)['paired_policy_members'][0]['utility_comparisons']==[]


def test_default_long_member_inventory_fits_metrics_budget(tmp_path):
    from development.evaluation.contracts import Population
    from development.evaluation.metrics.prediction import measure_prediction
    from .test_prediction_metrics import evidence
    plan=freeze_plan(default_plan(),ClosedRoot(tmp_path))
    inventory=expand_inventory(plan.plan)
    member=next(r.member for r in inventory if expected_metadata(plan,r)['dimensions']['family']=='B')
    from development.evaluation.registry import ACTIONS
    rows=[]
    for n in range(1,801):
        item=evidence(n,ACTIONS[(n-1)%4],support=min(200,n))
        data=json.loads(item.body)
        numeric=dict(status='predicted',value=50.,method='action_mean_delta',evidence_count=min(200,n),confidence=.95)
        boolean=dict(status='predicted',value=True,method='action_boolean_frequency',evidence_count=min(200,n),probability_true=.75,confidence=.95)
        data['prediction']['signals'].update(battery_pct=numeric,disk_free_pct=numeric,network_reachable=boolean)
        data['state_after'].update(battery_pct=49.75,disk_free_pct=49.95,network=True)
        data['baselines']['global-history']={'signals':copy.deepcopy(data['prediction']['signals'])}
        data['baselines']['persistence']['signals'].update(battery_pct=numeric,disk_free_pct=numeric,network_reachable={**boolean,'method':'persistence'})
        rows.append(replace(item,body=json.dumps(data).encode()))
    rows=tuple(rows)
    output=[]
    placeholders=fixture_measurements(plan)
    for slot in inventory:
        if slot.member!=member:continue
        dim=expected_metadata(plan,slot)['dimensions']
        if slot.metric.startswith('prediction.'):
            result=measure_prediction(slot.metric,rows,Population(dim['population'],(member,),dim['window'],slot.role),plan)
        else:
            result=placeholders[list(inventory).index(slot)]
        output.append(result)
    from development.evaluation.specs import raw_bytes
    actual_bytes=sum(len(raw_bytes(dict(identity=r.identity,metric=r.metric,version=r.version,member=r.member,state=r.state,role=r.role,data=json.loads(r.body))))+1 for r in output)
    assert actual_bytes<=256*1024
    primary=next(r for r in output if r.metric=='prediction.numeric-mae' and json.loads(r.body)['dimensions']['population']=='online-load-seed' and json.loads(r.body)['dimensions']['window']=='b-whole' and r.role=='PRIMARY')
    detail=json.loads(primary.body)
    assert detail['source_ordinals']=={'encoding':'inclusive_ranges','count':800,'ranges':[[1,800]]}
    assert detail['method_support']=={'encoding':'inclusive_support_ranges_with_count','ranges':[[1,199,1],[200,200,601]],'unavailable':0}



def test_oversized_member_cannot_enter_complete_suite_aggregate(tmp_path,plan_body):
    from .test_producer_metrics import plan
    frozen_plan=plan(tmp_path,plan_body)
    rows=[]
    for row in fixture_measurements(frozen_plan):
        data=json.loads(row.body);data['extra_detail']=['x'*4096]*3
        rows.append(replace(row,body=json.dumps(data).encode()))
    runs=(RunSummary('member-0',RunResult('COMPLETED',None)),)
    result=summarize_suite(frozen_plan,runs,tuple(rows))
    assert result['completed_valid_count']==0 and result['invalid_count']==1
    assert all(a['complete_run_count']==0 for a in result['aggregates'])


def test_absent_registered_suite_groups_and_reasons_remain_visible(tmp_path,plan_body):
    plan=admitted(tmp_path,plan_body)
    runs=(RunSummary('member-0',RunResult('FAILED','literal-before-output')),)
    result=summarize_suite(plan,runs,())
    assert result['failed_count']==1 and result['completed_valid_count']==0
    group=result['aggregates'][0]
    assert group['metric']=='prediction.numeric-mae'
    assert group['planned_run_count']==1 and group['failed_run_count']==1
    assert group['valid_run_count']==0 and group['complete_run_count']==0
    assert group['aggregation_state']=='UNAVAILABLE' and group['aggregation_reason']=='NO_COMPLETE_VALID_MEASUREMENT'
    assert group['sample_weighted_mean'] is None and group['per_run_mean'] is None
    assert len(group['missing_measurements'])==1
    assert result['members'][0]['missing_reasons'][group['missing_measurements'][0]]=='FAILED_MEMBER_MISSING_REGISTERED_MEASUREMENT'


def test_default_absent_suite_accounts_for_every_primary_group(tmp_path):
    plan=freeze_plan(default_plan(),ClosedRoot(tmp_path))
    result=summarize_suite(plan,(),())
    assert result['planned_count']==30 and result['planned_not_started_count']==30
    assert {g['metric'] for g in result['aggregates']}==set(METRICS)
    assert sum(g['planned_run_count'] for g in result['aggregates'])==sum(r.role=='PRIMARY' for r in expand_inventory(plan.plan))
    assert all(g['aggregation_state']=='UNAVAILABLE' for g in result['aggregates'])


@pytest.mark.parametrize('changes',[
    {'value':-.1,'numerator':-.1}, {'denominator':-3}, {'denominator':0},
    {'denominator':True}, {'denominator':1.5}, {'value':'perfect'},
    {'value':{'loss':0}}, {'value':False}, {'numerator':-.1},
    {'numerator':.8}, {'opportunities':0}, {'exclusions':1},
    {'eligibility_cross_tab':{'both':2,'seed_only':0,'baseline_only':0,'neither':0}},
    {'reason_cross_tab':{'eligible|eligible':2}}, {'coverage':{'seed':2}},
    {'source_ordinals':[1,2]}, {'methods':{'action_mean_delta':2}},
])
def test_genuine_numeric_report_rejects_malformed_math(tmp_path,plan_body,changes):
    from development.evaluation.contracts import Population
    from development.evaluation.metrics.prediction import measure_prediction
    from .test_prediction_metrics import evidence
    plan=admitted(tmp_path,classification_body(plan_body))
    real=measure_prediction('prediction.numeric-mae',(evidence(1),),Population('all',('member-0',)),plan)
    assert reconcile_output(plan,(real,),classify_questions(plan,(real,),'COMPLETED')).passed
    data=json.loads(real.body);data.update(changes)
    bad=replace(real,body=json.dumps(data).encode());rows=(bad,)
    findings=classify_questions(plan,rows,'COMPLETED')
    assert findings[0].status=='INCONCLUSIVE'
    assert not reconcile_output(plan,rows,findings).passed
    suite=summarize_suite(plan,(RunSummary('member-0',RunResult('COMPLETED',None)),),rows)
    assert suite['completed_valid_count']==0 and suite['invalid_count']==1
    assert suite['aggregates'][0]['per_run_mean'] is None


@pytest.mark.parametrize('metric,target,prediction,actual,probability',[
    ('prediction.numeric-mae','load_ratio',.4,.4,None),
    ('prediction.numeric-normalized-mae','load_ratio',2.,0.,None),
    ('prediction.boolean-accuracy','network_reachable',True,False,None),
    ('prediction.boolean-brier','network_reachable',True,False,.75),
])
def test_actual_scalar_metric_contracts_preserve_zero_and_unclipped_loss(tmp_path,plan_body,metric,target,prediction,actual,probability):
    from development.evaluation.contracts import Population
    from development.evaluation.metrics.prediction import measure_prediction
    from .test_prediction_metrics import evidence
    body=copy.deepcopy(plan_body);body['metrics']=[dict(id=metric,version=1)]
    body['questions'][0]['metrics']=[metric];body['populations'][0]['signal']='network' if target=='network_reachable' else target
    plan=admitted(tmp_path,body)
    row=measure_prediction(metric,(evidence(1,prediction=prediction,actual=actual,target=target,probability=probability,
        method='action_boolean_frequency' if probability is not None else 'action_mean_delta'),),Population('all',('member-0',)),plan)
    assert row.state=='MEASURED'
    assert reconcile_output(plan,(row,),classify_questions(plan,(row,),'COMPLETED')).passed
    if metric=='prediction.numeric-normalized-mae':assert row.value==2
    for value in (-.1,False,'zero',{},1.1) if target=='network_reachable' else (-.1,False,'zero',{}):
        data=json.loads(row.body);data.update(value=value,numerator=value)
        bad=replace(row,body=json.dumps(data).encode())
        assert not reconcile_output(plan,(bad,),classify_questions(plan,(bad,),'COMPLETED')).passed


@pytest.mark.parametrize('change',[{'value':.7},{'value':False},{'value':{}},{'standardized':{'early':-1.,'late':.5}}])
def test_actual_signed_window_change_requires_registered_math(tmp_path,plan_body,change):
    from development.evaluation.contracts import Population
    from development.evaluation.metrics.prediction import measure_prediction
    from .test_prediction_metrics import evidence
    body=copy.deepcopy(plan_body);body['metrics']=[dict(id='prediction.window-change',version=1)]
    body['questions'][0]['metrics']=['prediction.window-change'];body['members'][0]['measured']=400
    body['windows'][0]['end']=400
    plan=admitted(tmp_path,body)
    samples=tuple(evidence(n,prediction=.5 if n<100 else .9) for n in [1,2,3,4,5,361,362,363,364,365])
    row=measure_prediction('prediction.window-change',samples,Population('all',('member-0',)),plan)
    assert row.value<0 and reconcile_output(plan,(row,),classify_questions(plan,(row,),'COMPLETED')).passed
    data=json.loads(row.body);data.update(change);bad=replace(row,body=json.dumps(data).encode())
    assert not reconcile_output(plan,(bad,),classify_questions(plan,(bad,),'COMPLETED')).passed


@pytest.mark.parametrize('n',[1,5])
@pytest.mark.parametrize('defect',['top_negative','top_bool','top_string','top_object','top_math',
    'total_missing','total_negative','total_math','stratum_negative','stratum_bool','stratum_string','stratum_math','stratum_null_rule'])
def test_genuine_paired_counterpart_rejects_malformed_loss(tmp_path,plan_body,n,defect):
    from development.evaluation.contracts import Population
    from development.evaluation.metrics.prediction import measure_prediction
    from .test_prediction_metrics import evidence
    body=classification_body(plan_body);body['populations'][0]['comparison']='persistence'
    body['members'][0]['measured']=n;body['windows'][0]['end']=n
    plan=admitted(tmp_path,body)
    row=measure_prediction('prediction.numeric-mae',tuple(evidence(i,baseline=.6) for i in range(1,n+1)),Population('all',('member-0',)),plan)
    assert reconcile_output(plan,(row,),classify_questions(plan,(row,),'COMPLETED')).passed
    data=json.loads(row.body);stratum=data['action_strata']['rest']
    if defect.startswith('top_'):data['baseline_value']={'top_negative':-.2,'top_bool':False,'top_string':'perfect','top_object':{},'top_math':.8}[defect]
    elif defect=='total_missing':data.pop('baseline_numerator',None)
    elif defect.startswith('total_'):data['baseline_numerator']=-1. if defect=='total_negative' else 42.
    elif defect=='stratum_negative':stratum['baseline_numerator']=-1.
    elif defect=='stratum_bool':stratum['baseline_value']=False
    elif defect=='stratum_string':stratum['baseline_value']='perfect'
    elif defect=='stratum_math':stratum['baseline_value']=42.
    else:stratum['baseline_value']=.2 if n<5 else None
    bad=replace(row,body=json.dumps(data).encode());rows=(bad,)
    findings=classify_questions(plan,rows,'COMPLETED')
    assert findings[0].status=='INCONCLUSIVE'
    assert not reconcile_output(plan,rows,findings).passed
    summary=summarize_suite(plan,(RunSummary('member-0',RunResult('COMPLETED',None)),),rows)
    assert summary['completed_valid_count']==0 and summary['invalid_count']==1


@pytest.mark.parametrize('metric',['prediction.coverage','prediction.support-counts'])
def test_structured_prediction_supplemental_counterpart_is_validated(tmp_path,plan_body,metric):
    from development.evaluation.contracts import Population
    from development.evaluation.metrics.prediction import measure_prediction
    from .test_prediction_metrics import evidence
    body=copy.deepcopy(plan_body);body['metrics']=[dict(id=metric,version=1)]
    body['questions'][0]['metrics']=[metric];body['populations'][0]['comparison']='persistence'
    plan=admitted(tmp_path,body)
    row=measure_prediction(metric,(evidence(1,baseline=.6),),Population('all',('member-0',)),plan)
    assert reconcile_output(plan,(row,),classify_questions(plan,(row,),'COMPLETED')).passed
    data=json.loads(row.body);data['baseline_value']=-.2;bad=replace(row,body=json.dumps(data).encode())
    assert not reconcile_output(plan,(bad,),classify_questions(plan,(bad,),'COMPLETED')).passed


@pytest.mark.parametrize('n',[1,5])
def test_paired_counterpart_zero_unclipped_and_absent_comparison(tmp_path,plan_body,n):
    from development.evaluation.contracts import Population
    from development.evaluation.metrics.prediction import measure_prediction
    from .test_prediction_metrics import evidence
    body=copy.deepcopy(plan_body);body['metrics']=[dict(id='prediction.numeric-normalized-mae',version=1)]
    body['questions'][0]['metrics']=['prediction.numeric-normalized-mae'];body['populations'][0]['comparison']='persistence'
    body['members'][0]['measured']=n;body['windows'][0]['end']=n
    plan=admitted(tmp_path,body)
    for baseline in (0.,2.):
        row=measure_prediction('prediction.numeric-normalized-mae',tuple(evidence(i,prediction=0.,actual=0.,baseline=baseline) for i in range(1,n+1)),Population('all',('member-0',)),plan)
        data=json.loads(row.body)
        assert data['baseline_numerator']==n*baseline and data['baseline_value']==baseline
        assert reconcile_output(plan,(row,),classify_questions(plan,(row,),'COMPLETED')).passed
    other=tmp_path/'absent';other.mkdir();body['populations'][0]['comparison']=None
    without=admitted(other,body)
    row=measure_prediction('prediction.numeric-normalized-mae',(evidence(1),),Population('all',('member-0',)),without)
    assert json.loads(row.body)['baseline_value'] is None
    data=json.loads(row.body);data['baseline_value']=.1;bad=replace(row,body=json.dumps(data).encode())
    assert not reconcile_output(without,(bad,),classify_questions(without,(bad,),'COMPLETED')).passed


@pytest.mark.parametrize('n',[0,1])
@pytest.mark.parametrize('defect',['negative','boolean','non_null_below_minimum','wrong_total','wrong_count'])
def test_unavailable_paired_loss_retains_validated_null_summary(tmp_path,plan_body,n,defect):
    from development.evaluation.contracts import Population
    from development.evaluation.metrics.prediction import measure_prediction
    from .test_prediction_metrics import evidence
    body=copy.deepcopy(plan_body);body['populations'][0].update(action='rest',comparison='persistence')
    plan=admitted(tmp_path,body)
    row=measure_prediction('prediction.numeric-mae',tuple(evidence(i,baseline=.6) for i in range(1,n+1)),Population('all',('member-0',)),plan)
    assert row.state=='UNAVAILABLE' and row.value is None
    assert reconcile_output(plan,(row,),classify_questions(plan,(row,),'COMPLETED')).passed
    data=json.loads(row.body)
    if defect in ('negative','boolean','non_null_below_minimum'):data['baseline_value']={'negative':-.2,'boolean':False,'non_null_below_minimum':.2}[defect]
    elif defect=='wrong_total':data['baseline_numerator']=42.
    else:data['denominator']=5
    bad=replace(row,body=json.dumps(data).encode())
    assert not reconcile_output(plan,(bad,),classify_questions(plan,(bad,),'COMPLETED')).passed
    data.pop('opportunities');incomplete=replace(row,body=json.dumps(data).encode())
    assert not reconcile_output(plan,(incomplete,),classify_questions(plan,(incomplete,),'COMPLETED')).passed
    summary=summarize_suite(plan,(RunSummary('member-0',RunResult('COMPLETED',None)),),(bad,))
    assert summary['completed_valid_count']==0 and summary['invalid_count']==1


@pytest.mark.parametrize('metric',['prediction.coverage','prediction.support-counts'])
def test_absent_paired_structured_evidence_is_null_and_accounted(tmp_path,plan_body,metric):
    from development.evaluation.contracts import Population
    from development.evaluation.metrics.prediction import measure_prediction
    body=copy.deepcopy(plan_body);body['metrics']=[dict(id=metric,version=1)];body['questions'][0]['metrics']=[metric]
    body['populations'][0]['comparison']='persistence';plan=admitted(tmp_path,body)
    row=measure_prediction(metric,(),Population('all',('member-0',)),plan)
    assert row.state=='UNAVAILABLE' and reconcile_output(plan,(row,),classify_questions(plan,(row,),'COMPLETED')).passed
    data=json.loads(row.body);data['baseline_numerator']=1.;bad=replace(row,body=json.dumps(data).encode())
    assert not reconcile_output(plan,(bad,),classify_questions(plan,(bad,),'COMPLETED')).passed
    data.pop('opportunities');incomplete=replace(row,body=json.dumps(data).encode())
    assert not reconcile_output(plan,(incomplete,),classify_questions(plan,(incomplete,),'COMPLETED')).passed
