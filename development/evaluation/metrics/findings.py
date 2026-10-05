"""Complete preregistered accounting. Execution success is not scientific success."""
from collections import Counter
import math
import statistics

from ..analysis import expand_inventory
from ..contracts import ContractError, Measurement, QuestionFinding, RunSummary, VerificationReport, strict_json
from .registry import expected_metadata, measurement_data, plan_data
from ..specs import raw_bytes

EXECUTION = ('PLANNED','RUNNING','COMPLETED','INCOMPLETE','FAILED','INVALID')
FINDINGS = ('POSITIVE','MIXED','NEGATIVE','INCONCLUSIVE','NOT_EVALUATED')


def _valid_row(plan,row):
    if type(row) is not Measurement or row.state not in ('MEASURED','UNAVAILABLE','NOT_EVALUATED'):
        return False
    try:
        expected=expected_metadata(plan,row);data=measurement_data(row)
        if data.get('plan_digest')!=plan.digest or data.get('dimensions')!=expected['dimensions']:
            return False
        if data.get('non_inferential',False)!=(row.role=='EXPLORATORY_DIAGNOSTIC'):
            return False
        if (row.value is None)!=(row.state!='MEASURED') or (row.state!='MEASURED' and not row.reason):
            return False
        if not expected['applicable'] and (row.state!='NOT_EVALUATED' or row.reason!=expected['reason']):
            return False
        if row.state=='MEASURED' and row.metric in ('decision.constraints','decision.eligibility','curiosity.bounds'):
            key='mismatched' if row.metric=='decision.eligibility' else 'violations'
            if type(row.value) is not dict or type(row.value.get(key)) is not int or row.value[key]!=0:return False
        if expected['applicable'] and row.state=='NOT_EVALUATED':
            return False
    except (ValueError,TypeError,KeyError,OverflowError,RecursionError):
        return False
    return True


def classify_questions(plan,measurements,execution_status):
    body=plan_data(plan)
    if execution_status not in EXECUTION or type(measurements) is not tuple:
        raise ContractError()
    output=[]
    thresholds={t['id']:t for t in body['thresholds']}
    for question in body['questions']:
        if execution_status=='INVALID':status,reason='NOT_EVALUATED','INVALID_NO_VALID_SCIENTIFIC_EXECUTION'
        elif execution_status in ('PLANNED','RUNNING'):status,reason='NOT_EVALUATED','EXECUTION_NOT_COMPLETED'
        elif execution_status in ('FAILED','INCOMPLETE'):status,reason='INCONCLUSIVE','INCOMPLETE_EXECUTION_DEPENDENT_EVIDENCE'
        elif question['rule']=='descriptive_only':status,reason='NOT_EVALUATED','DESCRIPTIVE_ONLY_NO_CLASSIFICATION_RULE'
        else:
            selected=[m for m in measurements if type(m) is Measurement and m.metric in question['metrics'] and m.role=='PRIMARY']
            expected=[m for m in expand_inventory(plan.plan) if m.metric in question['metrics'] and m.role=='PRIMARY']
            if set(m.identity for m in selected)!=set(m.identity for m in expected) or any(not _valid_row(plan,m) for m in selected):
                status,reason='INCONCLUSIVE','MISSING_OR_INVALID_REGISTERED_MEASUREMENT'
            elif selected and all(m.state=='NOT_EVALUATED' for m in selected):
                status,reason='NOT_EVALUATED','NOT_APPLICABLE_TO_REGISTERED_PROTOCOL_OR_FAMILY'
            else:
                predicates=[];unavailable=False
                for identity in question['thresholds']:
                    threshold=thresholds[identity]
                    relevant=[m for m in selected if m.metric==threshold['metric'] and measurement_data(m)['dimensions']['population']==threshold['population']]
                    if not relevant:unavailable=True
                    for row in relevant:
                        if row.state=='NOT_EVALUATED':continue
                        if row.state!='MEASURED' or type(row.value) not in (int,float):unavailable=True;continue
                        value=row.value;boundary=threshold['value']
                        predicates.append(value<=boundary if threshold['direction']=='le' else value>=boundary if threshold['direction']=='ge' else value==boundary)
                if unavailable or not predicates:status,reason='INCONCLUSIVE','INSUFFICIENT_REGISTERED_EVIDENCE'
                elif all(predicates):status,reason='POSITIVE','PREREGISTERED_THRESHOLD_RULE'
                elif not any(predicates):status,reason='NEGATIVE','PREREGISTERED_THRESHOLD_RULE'
                else:status,reason='MIXED','PREREGISTERED_THRESHOLD_RULE'
        output.append(QuestionFinding(question['id'],status,reason,execution_status))
    return tuple(output)


def _member_bytes(rows):
    return sum(len(raw_bytes(dict(identity=m.identity,metric=m.metric,version=m.version,
        member=m.member,state=m.state,role=m.role,data=measurement_data(m))))+1 for m in rows)


def reconcile_output(plan,measurements,findings):
    body=plan_data(plan);expected=expand_inventory(plan.plan)
    reasons=[]
    if type(measurements) is not tuple or type(findings) is not tuple:
        return VerificationReport('SCIENTIFIC_REPORT',False,('SCIENTIFIC_REPORT_INVALID','INVALID_OUTPUT_CONTAINER'))
    counts=Counter(m.identity for m in measurements if type(m) is Measurement)
    expected_ids={m.identity for m in expected}
    if set(counts)!=expected_ids:reasons.append('REGISTERED_INVENTORY_MISMATCH')
    if any(count!=1 for count in counts.values()):reasons.append('DUPLICATE_MEASUREMENT')
    if any(not _valid_row(plan,m) for m in measurements):reasons.append('INVALID_VERSION_DIMENSIONS_STATE_OR_ROLE')
    question_ids={q['id'] for q in body['questions']}
    questions=Counter(f.question for f in findings if type(f) is QuestionFinding)
    if set(questions)!=question_ids or any(n!=1 for n in questions.values()):reasons.append('QUESTION_INVENTORY_MISMATCH')
    if any(type(f) is not QuestionFinding or f.status not in FINDINGS or not f.reason for f in findings):reasons.append('INVALID_FINDING')
    # A descriptive question cannot be silently promoted to a threshold claim.
    by_question={f.question:f for f in findings if type(f) is QuestionFinding}
    for q in body['questions']:
        if q['rule']=='descriptive_only' and q['id'] in by_question and by_question[q['id']].status in ('POSITIVE','NEGATIVE','MIXED'):
            reasons.append('UNREGISTERED_CLASSIFICATION')
    executions={f.execution for f in findings if type(f) is QuestionFinding}
    if len(executions)!=1 or not executions<=set(EXECUTION):
        reasons.append('INVALID_CLASSIFICATION_EXECUTION_CONTEXT')
    elif {f.question:f for f in findings}!={f.question:f for f in classify_questions(plan,measurements,next(iter(executions)))}:
        reasons.append('CLASSIFICATION_RULE_MISMATCH')
    try:
        if any(_member_bytes([m for m in measurements if type(m) is Measurement and m.member==member['id']])>256*1024 for member in body['members']):
            reasons.append('METRICS_BYTES_EXCEEDED')
    except (ValueError,TypeError,KeyError,OverflowError,RecursionError):
        reasons.append('MALFORMED_MEASUREMENT')
    if reasons:return VerificationReport('SCIENTIFIC_REPORT',False,('SCIENTIFIC_REPORT_INVALID',*tuple(dict.fromkeys(reasons))))
    return VerificationReport('SCIENTIFIC_REPORT',True,())


def _statistics(rows):
    values=[r.value for r in rows if type(r.value) in (int,float)]
    numerators=[];denominators=[]
    for row in rows:
        data=measurement_data(row)
        n,d=data.get('numerator'),data.get('denominator')
        if type(row.value) in (int,float) and type(n) in (int,float) and type(d) in (int,float) and d>0:
            numerators.append(n);denominators.append(d)
    denominator=math.fsum(denominators)
    return dict(sample_weighted_mean=math.fsum(numerators)/denominator if denominator else None,
        sample_denominator=denominator if denominator else None,per_run_mean=math.fsum(values)/len(values) if values else None,
        median=statistics.median(values) if values else None,min=min(values) if values else None,max=max(values) if values else None,
        measured_run_count=sum(r.state=='MEASURED' for r in rows),numeric_run_count=len(values))


def summarize_suite(plan,runs,measurements):
    body=plan_data(plan)
    if type(runs) is not tuple or type(measurements) is not tuple or any(type(r) is not RunSummary for r in runs):
        raise ContractError()
    planned={m['id']:m for m in body['members']}
    if any(type(m) is not Measurement or m.member not in planned for m in measurements):
        raise ContractError()
    if len({r.identity for r in runs})!=len(runs) or any(r.identity not in planned or r.execution.status not in EXECUTION for r in runs):
        raise ContractError()
    summaries={r.identity:r for r in runs}
    expected=expand_inventory(plan.plan);states={};members=[]
    for identity,member in planned.items():
        run=summaries.get(identity)
        status=run.execution.status if run else 'PLANNED'
        actual=[m for m in measurements if m.member==identity]
        expected_ids={m.identity for m in expected if m.member==identity}
        inventory_valid=(Counter(m.identity for m in actual)==Counter(expected_ids) and all(_valid_row(plan,m) for m in actual))
        if inventory_valid and _member_bytes(actual)>256*1024:inventory_valid=False
        valid=status=='COMPLETED' and inventory_valid
        data=strict_json(run.body) if run else {}
        states[identity]=(status,valid)
        members.append(dict(id=identity,seed=member['seed'],family=member['family'],variant=member['variant'],execution=status,
            execution_reason=run.execution.reason if run else None,report_valid=inventory_valid,completed_valid=valid,
            completed_prefix=data.get('completed_prefix'),checkpoints=data.get('checkpoints',[]),
            missing_measurements=sorted(expected_ids-{m.identity for m in actual}),
            missing_reasons={**{i:status+'_MEMBER_MISSING_REGISTERED_MEASUREMENT' for i in expected_ids-{m.identity for m in actual}},**{m.identity:m.reason for m in actual if m.state!='MEASURED'}},initial_digest=data.get('initial_digest')))
    groups={}
    def group_key(row):
        dim=expected_metadata(plan,row)['dimensions']
        return (row.metric,row.version,dim['family'],dim['protocol'],dim['variant'],dim['population'],dim['window'])
    for row in expected:
        if row.role!='PRIMARY':continue
        group=groups.setdefault(group_key(row),dict(expected=[],complete=[],prefix=[],qualifying_sets=set()))
        group['expected'].append(row)
    produced={row.identity:row for row in measurements}
    for row in measurements:
        if not _valid_row(plan,row) or row.role!='PRIMARY':continue
        data=measurement_data(row)
        group=groups[group_key(row)]
        status,valid=states[row.member]
        if valid:
            group['complete'].append(row)
            if row.metric=='prediction.window-change' and row.state=='MEASURED':
                group['qualifying_sets'].add(tuple(data.get('qualifying_actions',[])))
        elif status=='INCOMPLETE':group['prefix'].append(row)
    aggregates=[]
    for key,group in sorted(groups.items()):
        incompatible=len(group['qualifying_sets'])>1
        stats=_statistics(group['complete']) if not incompatible else {k:None for k in ('sample_weighted_mean','sample_denominator','per_run_mean','median','min','max','measured_run_count','numeric_run_count')}
        execution_counts=Counter(states[row.member][0] for row in group['expected'])
        measured_count=sum(row.state=='MEASURED' for row in group['complete'])
        numeric_count=sum(type(row.value) in (int,float) for row in group['complete'])
        aggregation_state='UNAVAILABLE' if incompatible or not measured_count else 'MEASURED' if numeric_count else 'NOT_EVALUATED'
        aggregation_reason='CHANGED_QUALIFYING_ACTION_SET' if incompatible else 'NO_COMPLETE_VALID_MEASUREMENT' if not measured_count else 'STRUCTURED_METRIC_HAS_NO_SCALAR_AGGREGATE' if not numeric_count else None
        aggregates.append(dict(metric=key[0],version=key[1],family=key[2],protocol=key[3],variant=key[4],population=key[5],window=key[6],
            **stats,planned_run_count=len(group['expected']),valid_run_count=measured_count,
            failed_run_count=execution_counts['FAILED'],incomplete_run_count=execution_counts['INCOMPLETE'],
            invalid_run_count=sum(states[row.member][0]=='INVALID' or states[row.member][0]=='COMPLETED' and not states[row.member][1] for row in group['expected']),
            aggregation_state=aggregation_state,aggregation_reason=aggregation_reason,
            missing_measurements=[row.identity for row in group['expected'] if row.identity not in produced],
            complete_run_count=len(group['complete']),incomplete_prefix_count=len(group['prefix']),
            incomplete_prefix_descriptive=_statistics(group['prefix']),population_compatible=not incompatible,
            incompatible_reason='CHANGED_QUALIFYING_ACTION_SET' if incompatible else None))
    paired=[]
    for seed in body['seeds']:
        pair=[m for m in members if m['family']=='D' and m['seed']==seed]
        if not pair:continue
        by_variant={m['variant']:m for m in pair}
        missing=[role for role in ('seed','random-eligible') if role not in by_variant or not by_variant[role]['completed_valid']]
        same_start=len(pair)==2 and pair[0]['initial_digest'] is not None and pair[0]['initial_digest']==pair[1]['initial_digest']
        eligible=not missing and same_start
        comparisons=[]
        if eligible:
            utilities={role:{} for role in ('seed','random-eligible')}
            for role,member in by_variant.items():
                for row in measurements:
                    if row.member==member['id'] and row.metric=='decision.task-utility' and row.role=='PRIMARY':
                        dim=measurement_data(row)['dimensions']
                        utilities[role][(dim['population'],dim['window'])]=row
            for key in sorted(set(utilities['seed'])|set(utilities['random-eligible'])):
                left=utilities['seed'].get(key);right=utilities['random-eligible'].get(key)
                available=left is not None and right is not None and left.state==right.state=='MEASURED' and type(left.value) in (int,float) and type(right.value) in (int,float)
                comparisons.append(dict(population=key[0],window=key[1],
                    seed_measurement=left.identity if left else None,random_eligible_measurement=right.identity if right else None,
                    seed_minus_random_eligible=math.fsum((left.value,-right.value)) if available else None,
                    reason=None if available else 'MISSING_TASK_UTILITY',
                    interpretation='separate_trajectories_equal_start_external_utility'))
        paired.append(dict(seed=seed,eligible=eligible,missing_or_incomplete_members=missing,utility_comparisons=comparisons,
            reason=None if eligible else 'MISSING_OR_INCOMPLETE_POLICY_MEMBER' if missing else 'UNVERIFIED_EQUAL_INITIAL_STATE',
            prediction_pairing='not_paired_divergent_policy_trajectories'))
    if all(valid for _,valid in states.values()):suite_execution='COMPLETED'
    elif all(status=='PLANNED' for status,_ in states.values()):suite_execution='PLANNED'
    elif any(status=='RUNNING' for status,_ in states.values()):suite_execution='RUNNING'
    elif all(status=='INVALID' for status,_ in states.values()):suite_execution='INVALID'
    else:suite_execution='INCOMPLETE'
    questions=classify_questions(plan,measurements,suite_execution)
    result=dict(planned_count=len(planned),completed_valid_count=sum(valid for _,valid in states.values()),
        incomplete_count=sum(status=='INCOMPLETE' for status,_ in states.values()),failed_count=sum(status=='FAILED' for status,_ in states.values()),
        invalid_count=sum(status=='INVALID' or (status=='COMPLETED' and not valid) for status,valid in states.values()),
        planned_not_started_count=sum(status=='PLANNED' for status,_ in states.values()),running_count=sum(status=='RUNNING' for status,_ in states.values()),
        members=members,aggregates=aggregates,paired_policy_members=paired,analysis_plan_digest=plan.digest,
        execution_status=suite_execution,findings=[dict(question=f.question,status=f.status,reason=f.reason,execution=f.execution) for f in questions])

    # Admission covers the complete parent control summary, not only inventory.
    # Raw source journals remain separate; no oversized partial summary is emitted.
    import json
    try:
        encoded=json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    except (ValueError,TypeError,OverflowError,RecursionError):
        raise ContractError() from None
    if len(encoded)>4*1024**2:
        raise ContractError()
    return result
