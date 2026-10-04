"""Source-fidelity audits of published B4–B8 facts; never producer updates."""
from collections import Counter
import hashlib
import json
import math

from ..analysis import expand_inventory
from ..contracts import CompletedEvidence, ContractError, Population, strict_json
from ..registry import ACTIONS
from .registry import measured, plan_data


def _raw(value):
    if type(value) is dict and set(value) == {'raw_json_chunks'}:
        chunks = value['raw_json_chunks']
        if type(chunks) is not list or len(chunks)>4 or any(type(c) is not str or len(c)>4096 for c in chunks):
            raise ContractError()
        value = ''.join(chunks)
    if type(value) is not str or len(value)>16384:
        raise ContractError()
    return value


def _json(value):
    try:
        result = json.loads(_raw(value), parse_constant=lambda _: (_ for _ in ()).throw(ContractError()))
    except (ValueError, TypeError, RecursionError):
        raise ContractError() from None
    return result


def _table(source, name):
    table = source.get('tables', {}).get(name)
    if table is None:
        return None
    if type(table) is not list or len(table)>2048 or any(type(row) is not dict for row in table):
        raise ContractError()
    return table


def _world(source, metric):
    rows = _table(source, 'world_beliefs')
    pending = _table(source, 'world_pending')
    if rows is None:
        return None, 'MISSING_WORLD_SOURCE', {}
    if metric == 'world.evidence-count':
        return dict(beliefs={r['belief_key']:r['evidence_count'] for r in rows}, published=len(rows),
                    pending=None if pending is None else len(pending)), None, {}
    if metric == 'world.insufficient-evidence':
        return dict(published=len(rows), pending=None if pending is None else len(pending),
                    published_evidence_available=bool(rows)), None, {}
    if metric == 'world.contradictions':
        beliefs = {}
        for row in rows:
            n, c = row['evidence_count'], row['contradiction_count']
            if type(n) is not int or n<2 or type(c) is not int or not 0<=c<=n:
                raise ContractError()
            reference = min(.95,n/20)*(1-c/n)
            value = _json(row['value_json'])
            beliefs[row['belief_key']] = dict(count=c, evidence_count=n, scope=row['scope'], scope_value=row['scope_value'],
                mean_delta=value.get('mean_delta'), probability_true=value.get('probability_true'),
                confidence=row['confidence'], confidence_reference=reference,
                confidence_matches=math.isclose(row['confidence'],reference,rel_tol=0,abs_tol=1e-12),
                first_transition_id=row['source_first_transition_id'], last_transition_id=row['source_last_transition_id'])
        return dict(beliefs=beliefs), None, {}
    history = source.get('world_revisions')
    if not history:
        return None, 'MISSING_PUBLICATION_HISTORY', {}
    if type(history) is not list or len(history)>1024:
        raise ContractError()
    ordered = sorted(history,key=lambda r:r['ordinal'])
    if len({r['ordinal'] for r in ordered}) != len(ordered):
        raise ContractError()
    publications = [(r['ordinal'], b) for r in ordered for b in r['beliefs']]
    if metric == 'world.first-belief':
        first = next(((ordinal,b) for ordinal,b in publications if b['evidence_count']>=2),None)
        return (dict(first_publication_ordinal=first[0],belief_key=first[1]['belief_key'],
                     source_transition_id=first[1]['source_last_transition_id']) if first else None), 'INSUFFICIENT_EVIDENCE' if first is None else None, {}
    previous, changes = {}, []
    for ordinal,row in publications:
        key=row['belief_key']; value=_json(row['value_json'])
        scalar=value.get('mean_delta',value.get('probability_true'))
        old=previous.get(key)
        if old is not None and row['source_last_transition_id']!=old[1]:
            changes.append(dict(ordinal=ordinal,belief_key=key,absolute_change=abs(scalar-old[0]),
                                source_transition_id=row['source_last_transition_id']))
        previous[key]=(scalar,row['source_last_transition_id'])
    if metric == 'world.stability':
        groups={}
        for change in changes:groups.setdefault(change['belief_key'],[]).append(change['absolute_change'])
        value=dict(beliefs={key:dict(mean_absolute_change=math.fsum(values)/len(values),revisions=len(values)) for key,values in groups.items()}) if groups else None
        return value, 'NO_OBSERVED_REVISION' if not changes else None, dict(revisions=len(changes))
    first_rest=source.get('first_changed_rest_ordinal')
    if type(first_rest) is not int:
        return None, 'MISSING_CHANGED_ACTION_EXPOSURE', {}
    revision=next((c for c in changes if c['ordinal']>=first_rest and ':action:rest:' in c['belief_key']),None)
    return (dict(first_changed_rest_ordinal=first_rest,revision_ordinal=revision['ordinal'],
                 rest_exposure_transition_latency=revision['ordinal']-first_rest) if revision else None), 'NO_OBSERVED_REVISION' if revision is None else None, {}


def _curiosity(source, metric):
    rows = _table(source,'curiosity_assessments')
    if not rows:
        return None,'MISSING_CURIOSITY_SOURCE',{}
    unavailable=sum(r['status']=='unavailable' for r in rows)
    if metric=='curiosity.unavailable':
        return dict(unavailable=unavailable,assessments=len(rows)),None,{}
    evaluated=[r for r in rows if r['status']=='evaluated']
    if not evaluated:
        return None,'NO_EVALUATED_ASSESSMENT',{}
    if metric=='curiosity.bounds':
        violations=sum(type(r.get('score')) not in (int,float) or not math.isfinite(r['score']) or not 0<=r['score']<=1 for r in evaluated)
        return dict(violations=violations,assessments=len(evaluated)),None,{}
    facts=[]
    for row in evaluated:
        surprise, uncertainty, novelty = row['prediction_surprise'],row['uncertainty'],row['novelty']
        if any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in (surprise,uncertainty,novelty,row['coverage'])):
            raise ContractError()
        reference=surprise*(.5+.5*uncertainty)*(.5+.5*novelty)
        components=row.get('components', _json(row['components_json']) if 'components_json' in row else {})
        # Compare recorded prior component snapshots to separately captured
        # prior facts when present. Missing prior capture never becomes a match.
        prior=source.get('prior_world_by_transition',{}).get(str(row['transition_id']))
        b3=source.get('b3_by_transition',{}).get(str(row['transition_id']))
        aggregate=b3.get('aggregate',{}) if b3 else {}
        error,coverage=aggregate.get('mean_normalized_error'),aggregate.get('coverage')
        reference_surprise=error*coverage if type(error) in (int,float) and type(coverage) in (int,float) else None
        prior_checks=[]
        if prior is not None:
            from seed.world_model import contradicts
            for signal, component in components.get('signals',{}).items():
                snapshot=component.get('prior_belief')
                actual=prior.get(signal)
                matches=(snapshot is None and actual is None) or (snapshot is not None and actual is not None and
                    all(snapshot.get(k)==actual.get(k) for k in ('belief_key','scope','scope_value','evidence_count','confidence','source_last_transition_id'))
                    and snapshot.get('value')==(_json(actual['value_json']) if 'value_json' in actual else actual.get('value')))
                contradiction=None
                if actual is not None and 'value_json' in actual:
                    original=dict(actual,value_json=_raw(actual['value_json']))
                    contradiction=contradicts(signal,component['sample'],original)
                elif actual is None:contradiction=False
                prior_checks.append(dict(signal=signal,matches=matches,
                    contradiction_reference=contradiction,
                    contradiction_matches=component.get('contradictory')==contradiction if contradiction is not None else None))
        facts.append(dict(transition_id=row['transition_id'],actual_score=row['score'],reference_score=reference,
            matches=math.isclose(row['score'],reference,rel_tol=0,abs_tol=1e-12),
            prediction_surprise=surprise,coverage=row['coverage'],uncertainty=uncertainty,novelty=novelty,
            b3_reference_surprise=reference_surprise,
            b3_source_matches=math.isclose(surprise,reference_surprise,rel_tol=0,abs_tol=1e-12) if reference_surprise is not None else None,
            prior_source_checks=prior_checks,prior_source_status='captured' if prior is not None else 'unavailable'))
    return dict(formula_matches=sum(f['matches'] for f in facts),assessments=len(facts),facts=facts),None,{}


def _semantic(source,metric,protocol):
    if protocol=='FROZEN_SELECTION_ASSAY' and metric in ('semantic.promotion-latency','semantic.revisions','semantic.status-transitions'):
        return None,'FROZEN_PROTOCOL_SUPPRESSES_MUTATION',dict(state='NOT_EVALUATED')
    rows=_table(source,'semantic_memories'); runs=_table(source,'consolidation_runs')
    if metric=='semantic.promotion-latency':
        if not runs:return None,'NO_CONSOLIDATION_OPPORTUNITY',{}
        opportunities=source.get('semantic_eligibility_history')
        if not opportunities:return None,'MISSING_ELIGIBILITY_HISTORY',{}
        latencies=[]; eligible_count=0; exclusions=Counter()
        run_by_id={r['id']:r for r in runs}
        for event in opportunities:
            run=run_by_id.get(event.get('run_id'))
            if run is None:
                exclusions['missing_actual_run']+=1;continue
            result=_json(run['result_json'])
            if (run['status'] not in ('completed','completed_with_errors') or result.get('reason') is not None
                    or event['source_belief_id'] not in result.get('examined_ids',[])):
                exclusions['not_an_actual_eligible_opportunity']+=1;continue
            if event['support']>=8 and event['confidence']>=.30 and not event['resource_guard']:
                eligible_count+=1
                publication=next((r for r in rows or [] if r['source_belief_id']==event['source_belief_id'] and r['created_at']>=event['at']),None)
                if publication:latencies.append(dict(source_belief_id=event['source_belief_id'],eligible_at=event['at'],published_at=publication['created_at'],latency=publication['created_at']-event['at']))
        if not eligible_count:return None,'NO_ELIGIBLE_CONSOLIDATION_OPPORTUNITY',dict(exclusions=dict(exclusions))
        return dict(promotions=latencies,eligible_opportunities=eligible_count,exclusions=dict(exclusions)),None,{}
    if rows is None:return None,'MISSING_SEMANTIC_SOURCE',{}
    history=_table(source,'semantic_memory_history')
    if metric=='semantic.revisions':
        if history is None:return None,'MISSING_SEMANTIC_HISTORY',{}
        return dict(revisions=len(history),semantic_ids=sorted({r['semantic_memory_id'] for r in history})),None,{}
    if metric=='semantic.status-transitions':
        if history is None:return None,'MISSING_SEMANTIC_HISTORY',{}
        return dict(current_status_counts=dict(Counter(r['status'] for r in rows)),historical_status_counts=dict(Counter(_json(r['data_json'])['status'] for r in history))),None,{}
    beliefs=_table(source,'world_beliefs')
    if beliefs is None:return None,'MISSING_SEMANTIC_SOURCE_BELIEFS',{}
    by_id={b['id']:b for b in beliefs}
    from seed.semantic_memory import normalized_source
    facts=[]
    for row in rows:
        belief=by_id.get(row['source_belief_id']); normalized=None
        if belief is not None:
            try:
                original=dict(belief,value_json=_raw(belief['value_json']))
                normalized=normalized_source(original)
            except (ValueError,TypeError,KeyError,OverflowError,RecursionError):pass
        available=normalized is not None
        matched=available and row['source_fingerprint']==normalized['source_fingerprint']
        facts.append(dict(semantic_id=row['id'],source_belief_id=row['source_belief_id'],source_available=available,
            fingerprint_matches=matched,status=row['status'],source_unavailable_consistent=(row['status']=='source_unavailable' and not available),
            source_link_valid=belief is not None and row['source_first_transition_id']==belief['source_first_transition_id'] and row['source_last_transition_id']==belief['source_last_transition_id'],
            actual_support=row['evidence_count'],actual_confidence=row['confidence'],eligible_at_capture=row['evidence_count']>=8 and row['confidence']>=.30))
    return dict(matched=sum(f['fingerprint_matches'] for f in facts),valid_source_links=sum(f['source_link_valid'] for f in facts),
                facts=facts,cursor=_table(source,'consolidation_state'),opportunities=None if runs is None else len(runs)),None,{}


def _self(source,metric):
    snapshot=source.get('self_snapshot'); evidence=source.get('self_evidence')
    if snapshot is None or evidence is None:
        return None,'MISSING_SELF_SOURCE_EVIDENCE',dict(denominator=None)
    from seed.self_model import validate_snapshot,project_snapshot,envelopes,bounded_json,sensor_valid,_evaluation
    try:validate_snapshot(snapshot)
    except (ValueError,TypeError,KeyError,OverflowError,RecursionError):
        return dict(unsupported=1,claims=[dict(path='snapshot',reason='invalid_producer_contract')]),None,dict(denominator=1)
    checks=[]
    def check(path,actual,expected):
        supported=actual==expected and (type(actual) is type(expected) if type(actual) is bool or type(expected) is bool else True)
        checks.append(dict(path=path,supported=supported,actual=actual,expected=expected))
    transition=evidence.get('transition')
    if transition is None:return None,'MISSING_SELF_TRANSITION_SOURCE',dict(denominator=None)
    check('source_transition_id',snapshot['source_transition_id'],transition['id'])
    check('source_event_id',snapshot['source_event_id'],evidence['event_cutoff'])
    check('last_selected_action.value',snapshot['last_selected_action']['value'],transition['action'])
    try:state=bounded_json(transition['state'])
    except ValueError:state={}
    for name,field in snapshot['observations'].items():
        if field['status'] in ('available','stale'):
            check('observations.'+name+'.value',field['value'],state.get(name))
    storage=snapshot['memory']['storage']['value']
    for key in ('page_size','page_count','schema_version'):
        check('memory.storage.'+key,storage[key],evidence[key])
    check('memory.storage.logical_allocated_bytes',storage['logical_allocated_bytes'],evidence['page_size']*evidence['page_count'])
    for key,ids in evidence['counts'].items():
        # The 1001 boundary is an at-least bounded count, never a total.
        expected=dict(count=len(ids),relation='at_least' if len(ids)==1001 else 'exact')
        check('memory.storage.'+key,storage[key],expected)
    check('sources.observation.ids',snapshot['sources']['observation']['ids'],[transition['id']])
    evaluations=evidence.get('evaluations',[])
    check('sources.prediction_window.ids',snapshot['sources']['prediction_window']['ids'],sorted(r['id'] for r in evaluations))
    check('prediction_performance.window.raw_rows',snapshot['prediction_performance']['window']['value']['raw_rows'],len(evaluations))
    valid,scored=[],[]
    for row in evaluations:
        raw=row.get('evaluation')
        if raw is None:continue
        try:
            aggregate=_evaluation(raw)
        except (ValueError,TypeError,KeyError,OverflowError,RecursionError):continue
        if aggregate is not None and 0<=row['started_at']<=row['completed_at']<=snapshot['measured_at']:
            valid.append((row,aggregate))
            if aggregate['status']=='evaluated':scored.append((row,aggregate))
    for label,rows in (('coverage',valid),('score',scored)):
        claim=snapshot['prediction_performance'][label]['value']
        check('prediction_performance.'+label+'.samples',claim['samples'],len(rows))
        check('sources.prediction_'+label+'.ids',snapshot['sources']['prediction_'+label]['ids'],sorted(r['id'] for r,_ in rows))
        keys=(('mean','coverage'),) if label=='coverage' else (('mean_normalized_error','mean_normalized_error'),('accuracy_score','accuracy_score'))
        for output,input_key in keys:
            expected=math.fsum(a[input_key]/len(rows) for _,a in rows) if rows else None
            check('prediction_performance.'+label+'.'+output,claim[output],expected)
    check('sources.errors.ids',snapshot['sources']['errors']['ids'],sorted(r['id'] for r in evidence.get('errors',[])[:100]))
    run=evidence.get('consolidation')
    check('sources.consolidation.ids',snapshot['sources']['consolidation']['ids'],[run['id']] if run else [])
    runtime=evidence.get('runtime')
    if runtime is not None:
        try:data=bounded_json(runtime['data'])
        except ValueError:data={}
        actual=snapshot['memory']['runtime_reported']['value']
        if actual is not None:
            for key in ('heartbeat','last_successful_cycle','session_id'):
                check('memory.runtime_reported.'+key,actual[key],data.get(key))
    read_time=source.get('read_time',snapshot['measured_at'])
    projection=project_snapshot(snapshot,read_time)
    status_counts=dict(Counter(f['status'] for f in envelopes(projection)))
    if metric=='self.freshness':
        return dict(status_counts=status_counts,stale=status_counts.get('stale',0),built_at=snapshot['measured_at'],read_at=read_time),None,dict(denominator=len(list(envelopes(projection))))
    unsupported=[c for c in checks if not c['supported']]
    if metric=='self.unsupported-claims':
        return dict(unsupported=len(unsupported),claims=unsupported),None,dict(denominator=len(checks))
    return dict(checked=len(checks),supported=len(checks)-len(unsupported),unsupported=len(unsupported),claims=checks),None,dict(denominator=len(checks))


def _decisions(evidence,source,metric,family):
    from seed.decision import constraints
    from seed.decision_record import validate_record,prediction_digest
    facts=[]; q_facts=[]; utilities=[]
    for item in evidence:
        if type(item) is not CompletedEvidence:raise ContractError()
        raw=strict_json(item.body); capture=raw.get('capture',raw)
        record=capture.get('selection')
        if record is None:continue
        before=capture.get('state_before',record['current'])
        prediction=capture.get('selected_prediction',capture.get('prediction'))
        action=record['selected_action']
        if action not in ACTIONS or constraints(before,action):
            raise ContractError()  # mandatory zero hard-constraint violations
        try:validate_record(record,prediction=prediction,state_before=before,draft=record['transition_id'] is None)
        except (ValueError,TypeError,KeyError,OverflowError,RecursionError):raise ContractError() from None
        facts.append(dict(ordinal=item.key[2],decision_id=record['decision_id'],selection_mode=record['selection_mode'],
            completed_evidence_sha256=hashlib.sha256(item.body).hexdigest(),
            selected_prediction_sha256=record['selected_prediction_sha256'],
            action=action,prediction_link_matches=record['selected_prediction_sha256']==prediction_digest(prediction),
            eligible_actions=record['eligible_actions'],selection_candidates=record['selection_candidates'],
            choice_index=record['choice_index'],history=record['history'],
            resource_status_counts=dict(Counter(s['status'] for c in record['candidates'].values() for s in c['resource_forecasts'].values()))))
        updates=raw.get('updates',capture.get('updates',{}))
        q=updates.get('q'); transition=updates.get('b1',{}).get('transition')
        if q and transition:
            old=record['candidates'][action]['q_value']; visits=record['candidates'][action]['visits']
            reward=transition['legacy_reward']; expected=old+record['alpha']*(reward-old)
            q_facts.append(dict(decision_id=record['decision_id'],transition_id=transition['id'],
                expected_value=expected,actual_value=q['after']['value'],actual_visits=q['after']['visits'],
                matches=math.isclose(q['after']['value'],expected,rel_tol=0,abs_tol=1e-12) and q['after']['visits']==visits+1))
        if family=='D':
            from ..scenarios.constrained import task_utility
            utilities.append(task_utility(before,action))
    if metric=='decision.task-utility':
        if family!='D':return None,'NOT_APPLICABLE_TO_REGISTERED_PROTOCOL_OR_FAMILY',dict(state='NOT_EVALUATED')
        return (math.fsum(utilities)/len(utilities) if utilities else None),'MISSING_TASK_TRANSITIONS' if not utilities else None,dict(denominator=len(utilities) if utilities else None)
    if metric=='decision.skipped-fallback':
        skipped=source.get('skipped_attempts')
        if not facts and skipped is None:return None,'MISSING_DECISION_SOURCE',dict(denominator=None)
        return dict(skipped_attempts=None if skipped is None else len(skipped),fallback=sum(f['selection_mode']=='fallback' for f in facts),
                    completed_decisions=len(facts),skipped_reasons=None if skipped is None else dict(Counter(s['reason'] for s in skipped))),None,dict(denominator=len(facts))
    if not facts:return None,'MISSING_DECISION_SOURCE',dict(denominator=None)
    if metric=='decision.q-compatibility':
        if not q_facts:return None,'MISSING_Q_UPDATE_SOURCE',dict(denominator=None)
        return dict(matched=sum(f['matches'] for f in q_facts),mismatched=sum(not f['matches'] for f in q_facts),facts=q_facts),None,dict(denominator=len(q_facts))
    if metric=='decision.constraints':return dict(violations=0,checked=len(facts)),None,dict(denominator=len(facts))
    if metric=='decision.prediction-link':return dict(matched=sum(f['prediction_link_matches'] for f in facts),checked=len(facts)),None,dict(denominator=len(facts))
    return dict(structurally_valid=len(facts),facts=facts),None,dict(denominator=len(facts))


def measure_producers(evidence, sources, plan):
    if type(evidence) is not tuple or len(evidence)>1024 or type(sources) is not dict:
        raise ContractError()
    body=plan_data(plan)
    members={m['id']:m for m in body['members']}
    result=[]
    for registered in expand_inventory(plan.plan):
        metric=registered.metric
        if metric.startswith('prediction.'):continue
        source=sources.get(registered.member,{})
        if type(source) is not dict:raise ContractError()
        # Digest source facts without interpreting original producer JSON.
        try:raw=json.dumps(source,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        except (ValueError,TypeError,OverflowError,RecursionError):raise ContractError() from None
        if len(raw)>32*1024**2:raise ContractError()
        member=members[registered.member]
        _,_,population_id,window=registered.identity.split(':')
        population=Population(population_id,(registered.member,),window)
        if metric.startswith('world.'):value,reason,facts=_world(source,metric)
        elif metric.startswith('curiosity.'):value,reason,facts=_curiosity(source,metric)
        elif metric.startswith('semantic.'):value,reason,facts=_semantic(source,metric,member['protocol'])
        elif metric.startswith('self.'):value,reason,facts=_self(source,metric)
        else:
            # A flat tuple belongs to a single-member assay. A multi-member
            # input must provide each actual member's completed source evidence.
            selected=evidence if len(members)==1 else tuple(CompletedEvidence(tuple(e['key']),e['body'].encode()) for e in source.get('completed_evidence',[]))
            value,reason,facts=_decisions(selected,source,metric,member['family'])
        result.append(measured(metric,population,plan,value=value,reason=reason,
            source_digest=hashlib.sha256(b'SEED_B10_PRODUCER_SOURCES_V1\0'+raw).hexdigest(),
            source_cutoff=source.get('cutoff'),source_limits=source.get('limits'),**facts))
    return tuple(result)
