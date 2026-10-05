"""Source-fidelity audits of published B4–B8 facts; never producer updates."""
from collections import Counter
import hashlib
import json
import math

from ..analysis import expand_inventory
from ..contracts import CompletedEvidence, ContractError, Population, strict_json, validate_event_key
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


def _bounded_facts(facts):
    """All-input digest/count; fixed first-eight detail never used for inference."""
    raw=json.dumps(facts,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
    return dict(facts=facts[:8],fact_count=len(facts),
        facts_sha256=hashlib.sha256(b'SEED_B10_AUDIT_FACTS_V1\0'+raw).hexdigest(),
        diagnostic_sample_non_inferential=True,diagnostic_sample_count=min(8,len(facts)),
        diagnostic_sample_rule='first_eight_in_source_order')


def _source_equal(actual,expected):
    """Source JSON equality preserves Boolean types and complete membership."""
    if type(expected) is dict:
        return type(actual) is dict and actual.keys()==expected.keys() and all(_source_equal(actual[k],v) for k,v in expected.items())
    if type(expected) is list:
        return type(actual) is list and len(actual)==len(expected) and all(_source_equal(a,b) for a,b in zip(actual,expected))
    if type(actual) is bool or type(expected) is bool:return type(actual) is type(expected) and actual==expected
    return actual==expected


def _curiosity(source, metric, evidence):
    rows = _table(source,'curiosity_assessments')
    if not rows:
        return None,'MISSING_CURIOSITY_SOURCE',{}
    unavailable=sum(r['status']=='unavailable' for r in rows)
    if metric=='curiosity.unavailable':
        return dict(unavailable=unavailable,assessments=len(rows)),None,{}
    evaluated=[r for r in rows if r['status']=='evaluated']
    if metric=='curiosity.bounds':
        if not evaluated:return None,'NO_EVALUATED_ASSESSMENT',{}
        violations=sum(type(r.get('score')) not in (int,float) or not math.isfinite(r['score']) or not 0<=r['score']<=1 for r in evaluated)
        return dict(violations=violations,assessments=len(evaluated)),None,{}
    transitions={}
    for item in evidence:
        joined=strict_json(item.body);capture=joined.get('capture',joined)
        b1=joined.get('updates',capture.get('updates',{})).get('b1',{})
        transition=b1.get('transition')
        if b1.get('status')=='confirmed' and type(transition) is dict and transition.get('id')==b1.get('transition_id'):
            tid=str(transition['id'])
            if tid in transitions and transitions[tid]!=transition:raise ContractError()
            transitions[tid]=transition
    facts=[]
    for row in rows:
        surprise, uncertainty, novelty = row.get('prediction_surprise'),row.get('uncertainty'),row.get('novelty')
        if row['status']=='evaluated' and any(type(v) not in (int,float) or not math.isfinite(v) or not 0<=v<=1 for v in (surprise,uncertainty,novelty,row['coverage'])):
            raise ContractError()
        reference=surprise*(.5+.5*uncertainty)*(.5+.5*novelty) if row['status']=='evaluated' else None
        components=row.get('components', _json(row['components_json']) if 'components_json' in row else {})
        # Compare recorded prior component snapshots to separately captured
        # prior facts when present. Missing prior capture never becomes a match.
        prior=source.get('prior_world_by_transition',{}).get(str(row['transition_id']))
        b3=source.get('b3_by_transition',{}).get(str(row['transition_id']))
        transition=transitions.get(str(row['transition_id']))
        source_reference=None;source_missing=[]
        if prior is None:source_missing.append('prior_b4')
        if b3 is None:source_missing.append('b3')
        if transition is None:source_missing.append('confirmed_b1_transition')
        if not source_missing:
            # Original pure reference only: no learning reimplementation,
            # producer update, additional source reads or assessment repair.
            from seed.curiosity import assess_curiosity
            original_prior={signal:dict(belief,value_json=_raw(belief['value_json'])) for signal,belief in prior.items()}
            source_reference=assess_curiosity(b3,_json(transition['state_before_json']),transition['action'],
                _json(transition['state_after_json']),original_prior)
        source_mismatches=[]
        if source_reference is not None:
            for key,expected in source_reference.items():
                actual=components if key=='components' else row.get(key)
                # SQLite stores the producer Boolean as an INTEGER column.
                if key=='reflection_eligible' and type(actual) is int and actual in (0,1):actual=bool(actual)
                if not _source_equal(actual,expected):source_mismatches.append(key)
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
            matches=math.isclose(row['score'],reference,rel_tol=0,abs_tol=1e-12) if reference is not None else None,
            prediction_surprise=surprise,coverage=row['coverage'],uncertainty=uncertainty,novelty=novelty,
            b3_reference_surprise=reference_surprise,
            b3_source_matches=math.isclose(surprise,reference_surprise,rel_tol=0,abs_tol=1e-12) if type(surprise) in (int,float) and reference_surprise is not None else None,
            source_status='UNAVAILABLE' if source_reference is None else 'MISMATCH' if source_mismatches else 'MATCH',
            source_mismatched_fields=source_mismatches,source_missing=source_missing,
            source_reference=source_reference,
            prior_source_checks=prior_checks,prior_source_status='captured' if prior is not None else 'unavailable'))
    if not evaluated and all(f['source_status']=='UNAVAILABLE' for f in facts):
        return None,'NO_EVALUATED_ASSESSMENT',{}
    return dict(formula_matches=sum(f['matches'] is True for f in facts),assessments=len(facts),
        source_matches=sum(f['source_status']=='MATCH' for f in facts),
        source_mismatches=sum(f['source_status']=='MISMATCH' for f in facts),
        source_unavailable=sum(f['source_status']=='UNAVAILABLE' for f in facts),
        b3_source_matches=sum(f['b3_source_matches'] is True for f in facts),
        b3_source_mismatches=sum(f['b3_source_matches'] is False for f in facts),
        b3_source_unavailable=sum(f['b3_source_matches'] is None for f in facts),
        prior_source_mismatches=sum(c['matches'] is False or c['contradiction_matches'] is False for f in facts for c in f['prior_source_checks']),
        prior_source_unavailable=sum(f['prior_source_status']=='unavailable' for f in facts),
        **_bounded_facts(facts)),None,{}


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
    from seed.semantic_memory import normalized_source, MODEL, MODEL_VERSION
    def normalize(belief):
        try:return normalized_source(dict(belief,value_json=_raw(belief['value_json'])))
        except (ValueError,TypeError,KeyError,OverflowError,RecursionError):return None
    # Independently captured source versions, never semantic claims as proof.
    versions={}
    current={b['id']:normalize(b) for b in beliefs}
    for reference in current.values():
        if reference is not None:versions.setdefault(reference['source_fingerprint'],[]).append(('current',reference))
    revisions=source.get('world_revisions',[])
    if type(revisions) is not list or len(revisions)>1024:raise ContractError()
    for revision in revisions:
        published=revision.get('beliefs')
        if type(published) is not list or len(published)>2048:raise ContractError()
        for belief in published:
            reference=normalize(belief)
            if reference is not None:versions.setdefault(reference['source_fingerprint'],[]).append(('historical',reference))
    facts=[]
    for row in rows:
        belief=by_id.get(row['source_belief_id']); normalized=current.get(row['source_belief_id'])
        available=normalized is not None
        matched=available and row['source_fingerprint']==normalized['source_fingerprint']
        candidates=versions.get(row['source_fingerprint'],[])
        version,reference=candidates[0] if candidates else ('unavailable',None)
        mismatches=[]
        if reference is not None:
            for key,value in reference.items():
                # Pure normalization deliberately excludes write-clock-only
                # changes from its fingerprint. Missing old clocks are not
                # false content; source clocks remain visible below.
                if key in ('source_belief_updated_at','payload_json'):continue
                actual=row.get(key)
                if actual!=value or (type(value) is int and type(actual) is not int):mismatches.append(key)
            try:payload_matches=_json(row['payload_json'])==_json(reference['payload_json'])
            except (ValueError,TypeError,KeyError,OverflowError,RecursionError):payload_matches=False
            if not payload_matches:mismatches.append('payload_json')
            for key,value in (('model',MODEL),('model_version',MODEL_VERSION)):
                if row.get(key)!=value or type(row.get(key)) is not type(value):mismatches.append(key)
        facts.append(dict(semantic_id=row['id'],source_belief_id=row['source_belief_id'],source_available=available,
            fingerprint_matches=matched,status=row['status'],source_unavailable_consistent=(row['status']=='source_unavailable' and not available),
            source_link_valid=belief is not None and row['source_first_transition_id']==belief['source_first_transition_id'] and row['source_last_transition_id']==belief['source_last_transition_id'],
            actual_support=row['evidence_count'],actual_confidence=row['confidence'],
            claimed_eligible=row['evidence_count']>=8 and row['confidence']>=.30,
            eligible_at_capture=normalized['evidence_count']>=8 and normalized['confidence']>=.30 if available else None,
            content_source_version=version,content_status='UNAVAILABLE' if reference is None else 'MISMATCH' if mismatches else 'MATCH',
            content_mismatched_fields=mismatches,
            reference_support=reference['evidence_count'] if reference else None,
            reference_confidence=reference['confidence'] if reference else None,
            claimed_source_updated_at=row.get('source_belief_updated_at'),
            captured_source_updated_at=reference['source_belief_updated_at'] if reference else None))
    return dict(matched=sum(f['fingerprint_matches'] for f in facts),valid_source_links=sum(f['source_link_valid'] for f in facts),
                content_matched=sum(f['content_status']=='MATCH' for f in facts),
                content_mismatched=sum(f['content_status']=='MISMATCH' for f in facts),
                content_unavailable=sum(f['content_status']=='UNAVAILABLE' for f in facts),
                **_bounded_facts(facts),cursor=_table(source,'consolidation_state'),opportunities=None if runs is None else len(runs)),None,{}


def _self(source,metric):
    snapshot=source.get('self_snapshot'); evidence=source.get('self_evidence')
    if snapshot is None or evidence is None:
        return None,'MISSING_SELF_SOURCE_EVIDENCE',dict(denominator=None)
    from seed.self_model import validate_snapshot,project_snapshot,envelopes,bounded_json,_evaluation,_observations,_age,_performance,_consolidation,_runtime,_failures,field as source_field,source as source_descriptor
    try:validate_snapshot(snapshot)
    except (ValueError,TypeError,KeyError,OverflowError,RecursionError):
        return dict(unsupported=1,claims=[dict(path='snapshot',reason='invalid_producer_contract')]),None,dict(denominator=1)
    checks=[];claims_by_path={}
    def check(path,actual,expected):
        supported=actual==expected and (type(actual) is type(expected) if type(actual) is bool or type(expected) is bool else True)
        if path not in claims_by_path:
            claim=dict(path=path,supported=supported,actual=actual,expected=expected,reference_checks=1)
            claims_by_path[path]=claim;checks.append(claim)
        else:
            claim=claims_by_path[path];claim['reference_checks']+=1
            # Independent references can disagree: retain that evidence on the
            # one claim, never multiply its denominator or silently discard it.
            if actual!=claim['actual'] or expected!=claim['expected']:
                claim.setdefault('reference_conflicts',[]).append(dict(actual=actual,expected=expected,supported=supported))
            claim['supported'] &= supported
    transition=evidence.get('transition')
    if transition is None:return None,'MISSING_SELF_TRANSITION_SOURCE',dict(denominator=None)
    check('source_transition_id',snapshot['source_transition_id'],transition['id'])
    check('source_event_id',snapshot['source_event_id'],evidence['event_cutoff'])
    check('last_selected_action.value',snapshot['last_selected_action']['value'],transition['action'])
    # Original pure envelope/source projection over independently captured rows.
    # No source reads, updates, whole-snapshot rebuild, or cognition duplication.
    reference_observations,observation_source=_observations(transition,snapshot['measured_at'])
    for key,expected in observation_source.items():
        check('sources.observation.'+key,snapshot['sources']['observation'][key],expected)
    check('sources.transition.source_observed_at',snapshot['sources']['transition']['source_observed_at'],transition['completed_at'])
    check('sources.transition.timestamp_kind',snapshot['sources']['transition']['timestamp_kind'],'completed_at')
    for name,field in snapshot['observations'].items():
        reference=_age(reference_observations[name],observation_source,snapshot['measured_at'],snapshot['measured_at'])
        for key in ('value','status','reason'):
            check('observations.'+name+'.'+key,field[key],reference[key])
    session_audit=dict(status='UNAVAILABLE',reason='MISSING_PUBLICATION_SESSION_SOURCE')
    if source.get('publication_session_id') is not None:
        check('source_session_id',snapshot['source_session_id'],source['publication_session_id'])
        session_audit=dict(status='MEASURED',matches=snapshot['source_session_id']==source['publication_session_id'])
    if source.get('publication_measured_at') is not None:
        check('measured_at',snapshot['measured_at'],source['publication_measured_at'])
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
    # Audit complete component envelopes from original, already captured rows.
    # These existing pure helpers neither read SQL nor rebuild/publish a snapshot.
    # Comparing the whole value keeps false absent/error claims in a fixed denominator.
    now=snapshot['measured_at']
    performance,performance_sources=_performance(evaluations,now)
    consolidation,consolidation_source=_consolidation(evidence.get('consolidation'),now)
    runtime,runtime_source=_runtime(evidence.get('runtime'),now)
    failures,error_source=_failures(evidence.get('errors',[]),now)
    reference_sources=dict(observation=observation_source,**performance_sources,
        transition=source_descriptor('transitions',[transition['id']],transition['completed_at'],'completed_at',60),
        storage=source_descriptor(None,[],now,'query_snapshot',60,
            tables=['seed_schema','episodes','transitions','world_model_queue','semantic_memories']),
        consolidation=consolidation_source,runtime=runtime_source,errors=error_source)
    for name,reference in reference_sources.items():
        for key,expected in reference.items():
            check('sources.'+name+'.'+key,snapshot['sources'][name][key],expected)
    references={'last_selected_action':source_field(transition['action'],'transition'),
        **{'prediction_performance.'+name:f for name,f in performance.items()},
        'memory.latest_consolidation':consolidation,'memory.runtime_reported':runtime,
        'recent_failures':failures}
    for path,reference in references.items():
        actual=snapshot
        for part in path.split('.'):actual=actual[part]
        reference=_age(reference,reference_sources[reference['source']],now,now)
        for key in ('value','status','reason','source'):check(path+'.'+key,actual[key],reference[key])
    storage_reference=_age(source_field(storage,'storage'),reference_sources['storage'],now,now)
    for key in ('status','reason','source'):
        check('memory.storage.'+key,snapshot['memory']['storage'][key],storage_reference[key])
    read_time=source.get('read_time',snapshot['measured_at'])
    projection=project_snapshot(snapshot,read_time)
    status_counts=dict(Counter(f['status'] for f in envelopes(projection)))
    if metric=='self.freshness':
        return dict(status_counts=status_counts,stale=status_counts.get('stale',0),
            basis='producer_claim_projection',source_faithful=all(c['supported'] for c in checks),
            session_audit=session_audit,built_at=snapshot['measured_at'],read_at=read_time),None,dict(denominator=len(list(envelopes(projection))))
    unsupported=[c for c in checks if not c['supported']]
    if metric=='self.unsupported-claims':
        return dict(unsupported=len(unsupported),claims=unsupported,session_audit=session_audit),None,dict(denominator=len(checks))
    return dict(checked=len(checks),supported=len(checks)-len(unsupported),unsupported=len(unsupported),claims=checks,session_audit=session_audit),None,dict(denominator=len(checks))


def _decisions(evidence,source,metric,family):
    from seed.decision import constraints
    from seed.learner import state_key
    from seed.decision_record import validate_record,prediction_digest,number,integer
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
        guard_checks={}
        for candidate_action in ACTIONS:
            expected_reasons=constraints(before,candidate_action)
            candidate=record['candidates'][candidate_action]
            guard_checks[candidate_action]=dict(expected_reasons=expected_reasons,
                actual_reasons=candidate['constraint_reasons'],actual_eligible=candidate['eligible'],
                matches=candidate['constraint_reasons']==expected_reasons and candidate['eligible']==(not expected_reasons))
        q_source=capture.get('q_snapshot')
        q_source_checks={}
        for candidate_action in ACTIONS:
            original=q_source.get(candidate_action) if type(q_source) is dict else None
            available=(type(original) is dict and number(original.get('q_value'))
                and integer(original.get('visits'),0) and type(original.get('q_missing')) is bool)
            actual={k:record['candidates'][candidate_action][k] for k in ('q_value','visits','q_missing')}
            q_source_checks[candidate_action]=dict(status='MEASURED' if available else 'UNAVAILABLE',
                reason=None if available else 'MISSING_OR_INVALID_PRESELECTION_Q_SOURCE',actual=actual,
                expected=original if available else None,matches=actual==original if available else None)
        facts.append(dict(ordinal=item.key[2],decision_id=record['decision_id'],selection_mode=record['selection_mode'],guard_checks=guard_checks,q_source_checks=q_source_checks,
            completed_evidence_sha256=hashlib.sha256(item.body).hexdigest(),
            selected_prediction_sha256=record['selected_prediction_sha256'],
            action=action,prediction_link_matches=record['selected_prediction_sha256']==prediction_digest(prediction),
            eligible_actions=record['eligible_actions'],selection_candidates=record['selection_candidates'],
            choice_index=record['choice_index'],history=record['history'],
            resource_status_counts=dict(Counter(s['status'] for c in record['candidates'].values() for s in c['resource_forecasts'].values()))))
        updates=raw.get('updates',capture.get('updates',{}))
        q=updates.get('q'); transition=updates.get('b1',{}).get('transition')
        source_available=(q_source_checks[action]['status']=='MEASURED' and type(q) is dict
            and type(q.get('before')) is dict and type(q.get('after')) is dict
            and type(transition) is dict and number(transition.get('legacy_reward'))
            and 'state_before_json' in transition and 'action' in transition and 'id' in transition)
        if source_available:
            original=q_source_checks[action]['expected']
            old,visits=original['q_value'],original['visits']
            reward=transition['legacy_reward'];expected=old+record['alpha']*(reward-old)
            try:transition_before=_json(transition['state_before_json'])
            except (ValueError,TypeError,AttributeError):transition_before=None
            links=dict(candidate=q_source_checks[action]['matches'],update_before=q['before']==original,
                state_key=record['state_key']==state_key(before),
                # SyntheticBody adds wall_time locally after recording the wire observation.
                # Compare the actual B1 state to that exact capture boundary; no defaults.
                state_before=(type(transition_before) is dict and
                    {k:v for k,v in transition_before.items() if k!='wall_time' or 'wall_time' in before}==before),
                selected_action=capture.get('selected_action')==action and transition['action']==action,
                transition_id=updates['b1'].get('transition_id')==transition['id']
                    and record['transition_id'] in (None,transition['id']),
                confirmed=q.get('status')=='confirmed' and updates['b1'].get('status')=='confirmed')
            update_matches=(number(q['after'].get('value')) and integer(q['after'].get('visits'),0)
                and math.isclose(q['after']['value'],expected,rel_tol=0,abs_tol=1e-12)
                and q['after']['visits']==visits+1)
            q_facts.append(dict(decision_id=record['decision_id'],transition_id=transition['id'],
                source_status='MEASURED',source_links=links,expected_value=expected,
                actual_value=q['after'].get('value'),actual_visits=q['after'].get('visits'),
                matches=all(links.values()) and update_matches))
        else:
            q_facts.append(dict(decision_id=record['decision_id'],source_status='UNAVAILABLE',
                reason='MISSING_OR_INVALID_Q_UPDATE_SOURCE',matches=None))
        if family=='D':
            from ..scenarios.constrained import task_utility
            utilities.append(task_utility(before,action))
    if metric=='decision.task-utility':
        if family!='D':return None,'NOT_APPLICABLE_TO_REGISTERED_PROTOCOL_OR_FAMILY',dict(state='NOT_EVALUATED')
        return (math.fsum(utilities)/len(utilities) if utilities else None),'MISSING_TASK_TRANSITIONS' if not utilities else None,dict(numerator=math.fsum(utilities) if utilities else None,denominator=len(utilities) if utilities else None)
    if metric=='decision.skipped-fallback':
        skipped=source.get('skipped_attempts')
        if not facts and skipped is None:return None,'MISSING_DECISION_SOURCE',dict(denominator=None)
        return dict(skipped_attempts=None if skipped is None else len(skipped),fallback=sum(f['selection_mode']=='fallback' for f in facts),
                    completed_decisions=len(facts),skipped_reasons=None if skipped is None else dict(Counter(s['reason'] for s in skipped))),None,dict(denominator=len(facts))
    if not facts:return None,'MISSING_DECISION_SOURCE',dict(denominator=None)
    if metric=='decision.q-compatibility':
        available=[f for f in q_facts if f['source_status']=='MEASURED']
        missing=len(q_facts)-len(available)
        if not available:return None,'MISSING_Q_UPDATE_SOURCE',dict(denominator=None,missing_source_updates=missing)
        return dict(matched=sum(f['matches'] is True for f in available),
            mismatched=sum(f['matches'] is False for f in available),missing_source_updates=missing,
            **_bounded_facts(q_facts)),None,dict(denominator=len(available))
    if metric=='decision.eligibility':
        return dict(structurally_valid=len(facts),checked_candidates=4*len(facts),
            matched=sum(c['matches'] for f in facts for c in f['guard_checks'].values()),
            mismatched=sum(not c['matches'] for f in facts for c in f['guard_checks'].values()),
            **_bounded_facts(facts)),None,dict(denominator=4*len(facts))
    if metric=='decision.constraints':return dict(violations=0,checked=len(facts)),None,dict(denominator=len(facts))
    if metric=='decision.prediction-link':return dict(matched=sum(f['prediction_link_matches'] for f in facts),checked=len(facts)),None,dict(denominator=len(facts))
    checks=[c for f in facts for c in f['q_source_checks'].values()]
    return dict(structurally_valid=len(facts),
        q_source_checked_candidates=sum(c['status']=='MEASURED' for c in checks),
        q_source_matched_candidates=sum(c['matches'] is True for c in checks),
        q_source_mismatched_candidates=sum(c['matches'] is False for c in checks),
        q_source_unavailable_candidates=sum(c['status']=='UNAVAILABLE' for c in checks),
        **_bounded_facts(facts)),None,dict(denominator=len(facts))


def _scoped_source(source,metric,definition,window,member,evidence):
    """Admit captured scope; missing event proof is never inferred from row IDs."""
    source=dict(source)
    tables=dict(source.get('tables',{}));source['tables']=tables
    end=16 if member['family']=='C' and definition.get('variant') else member['measured']
    whole=window['start']==1 and window['end']==end
    action,signal=definition['action'],definition['signal']
    target='network_reachable' if signal=='network' else signal
    def belief_matches(row):
        return (signal=='all' or row.get('signal')==target) and (action=='all' or row.get('scope')=='action' and row.get('scope_value')==action)
    if metric.startswith('world.'):
        history=source.get('world_revisions')
        if not whole and (not history or metric in ('world.first-belief','world.revision-latency')):
            return None,'MISSING_REGISTERED_SCOPE_EVIDENCE'
        if history is not None:
            if type(history) is not list or len(history)>1024:raise ContractError()
            default_phase=source.get('phase','measured' if member['training']==0 else None)
            if any(type(r.get('ordinal')) is not int or r.get('phase',default_phase) is None for r in history):
                return None,'MISSING_REGISTERED_SCOPE_EVIDENCE'
            history=[r for r in history if r.get('phase',default_phase)==definition['phase'] and window['start']<=r['ordinal']<=window['end']]
            source['world_revisions']=[dict(r,beliefs=[b for b in r['beliefs'] if belief_matches(b)]) for r in history]
            if not whole:
                if not history:return None,'MISSING_REGISTERED_SCOPE_EVIDENCE'
                last=max(history,key=lambda r:r['ordinal'])
                tables['world_beliefs']=last['beliefs']
                tables['world_pending']=last.get('pending')
        for name in ('world_beliefs','world_pending'):
            if tables.get(name) is not None:tables[name]=[r for r in _table(source,name) if belief_matches(r)]
        return source,'published_lifetime_at_capture' if whole else 'registered_publication_window'
    if metric.startswith('semantic.'):
        if not whole:return None,'MISSING_REGISTERED_SCOPE_EVIDENCE'
        if action!='all' or signal!='all':
            rows=_table(source,'semantic_memories')
            if rows is None:return None,'MISSING_REGISTERED_SCOPE_EVIDENCE'
            rows=[r for r in rows if belief_matches(r)];tables['semantic_memories']=rows
            ids={r['id'] for r in rows};belief_ids={r['source_belief_id'] for r in rows}
            if tables.get('semantic_memory_history') is not None:tables['semantic_memory_history']=[r for r in _table(source,'semantic_memory_history') if r['semantic_memory_id'] in ids]
            if source.get('semantic_eligibility_history') is not None:source['semantic_eligibility_history']=[r for r in source['semantic_eligibility_history'] if r['source_belief_id'] in belief_ids]
        return source,'published_lifetime_at_capture'
    if signal!='all':return None,'MISSING_REGISTERED_SCOPE_EVIDENCE'
    if whole and action=='all':return source,'published_lifetime_at_capture'
    events={}
    for item in evidence:
        raw=strict_json(item.body);capture=raw.get('capture',raw)
        tid=raw.get('updates',capture.get('updates',{})).get('b1',{}).get('transition_id')
        if tid is not None:
            events[tid]=(item.key,capture.get('selection',{}).get('selected_action',capture.get('selected_action')))
    def event_matches(tid):
        if tid not in events:return None
        key,selected=events[tid]
        return key[0]==definition['phase'] and window['start']<=key[2]<=window['end'] and (action=='all' or selected==action) and (definition.get('variant') is None or key[1]==definition['variant'])
    if metric.startswith('curiosity.'):
        rows=_table(source,'curiosity_assessments')
        if not rows or any(event_matches(r['transition_id']) is None for r in rows):return None,'MISSING_REGISTERED_SCOPE_EVIDENCE'
        tables['curiosity_assessments']=[r for r in rows if event_matches(r['transition_id'])]
    elif metric.startswith('self.'):
        snapshot=source.get('self_snapshot')
        if snapshot is None or event_matches(snapshot['source_transition_id']) is not True:return None,'MISSING_REGISTERED_SCOPE_EVIDENCE'
    return source,'registered_completed_event_scope'


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
        window=window.removesuffix('~exploratory')
        population=Population(population_id,(registered.member,),window,registered.role)
        definition=next(p for p in body['populations'] if p['id']==population_id)
        if definition.get('variant') is not None:
            source=source.get('variants',{}).get(definition['variant'],{})
        window_definition=next(w for w in body['windows'] if w['id']==window)
        selected=evidence if len(members)==1 else tuple(CompletedEvidence(tuple(e['key']),e['body'].encode()) for e in source.get('completed_evidence',[]))
        if len(selected)>1024 or any(type(e) is not CompletedEvidence for e in selected):raise ContractError()
        keys=[validate_event_key(list(e.key)) for e in selected]
        if len({key[:3] for key in keys})!=len(keys):raise ContractError()
        source_scope='registered_completed_event_scope'
        if not metric.startswith('decision.'):
            source,source_scope=_scoped_source(source,metric,definition,window_definition,member,selected)
        if source is None:
            value,reason,facts=None,'MISSING_REGISTERED_SCOPE_EVIDENCE',{}
            source={}
        elif metric.startswith('world.'):value,reason,facts=_world(source,metric)
        elif metric.startswith('curiosity.'):value,reason,facts=_curiosity(source,metric,selected)
        elif metric.startswith('semantic.'):value,reason,facts=_semantic(source,metric,member['protocol'])
        elif metric.startswith('self.'):value,reason,facts=_self(source,metric)
        else:
            # A flat tuple belongs to a single-member assay. A multi-member
            # input must provide each actual member's completed source evidence.
            selected=tuple(e for e in selected if e.key[0]==definition['phase'] and window_definition['start']<=e.key[2]<=window_definition['end']
                           and (definition.get('variant') is None or e.key[1]==definition['variant']))
            if definition['action']!='all':
                selected=tuple(e for e in selected if strict_json(e.body).get('capture',strict_json(e.body)).get('selection',{}).get('selected_action')==definition['action'])
            if definition['signal']!='all':value,reason,facts=None,'MISSING_REGISTERED_SCOPE_EVIDENCE',{}
            else:value,reason,facts=_decisions(selected,source,metric,member['family'])
        result.append(measured(metric,population,plan,value=value,reason=reason,
            source_scope=source_scope,source_digest=hashlib.sha256(b'SEED_B10_PRODUCER_SOURCES_V1\0'+raw).hexdigest(),
            source_cutoff=source.get('cutoff'),source_limits=source.get('limits'),**facts))
    return tuple(result)
