"""Closed versioned structured report contracts, without producer updates.

First-eight facts are diagnostics. Complete counters remain complete counters;
when all facts fit the sample their arithmetic is checked exactly, otherwise
sample contributions bound (but never replace) the complete counters.
"""
import hashlib
import json
import math

ACTIONS=('observe','reflect','consolidate','rest')
FACT_KEYS={'facts','fact_count','facts_sha256','diagnostic_sample_non_inferential',
           'diagnostic_sample_count','diagnostic_sample_rule'}


def need(condition):
    if not condition:raise ValueError('invalid structured measurement')


def count(v):return type(v) is int and v>=0

def number(v):return type(v) in (int,float) and math.isfinite(v)

def positive(v):return count(v) and v>0

def close(a,b):return number(a) and number(b) and math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-12)

def same(a,b):
    if type(a) is bool or type(b) is bool:return type(a) is type(b) and a==b
    if type(a) is dict and type(b) is dict:return set(a)==set(b) and all(same(a[k],b[k]) for k in a)
    if type(a) is list and type(b) is list:return len(a)==len(b) and all(same(x,y) for x,y in zip(a,b))
    return a==b


def shape(v,required,optional=()):
    need(type(v) is dict and set(required)<=set(v)<=set(required)|set(optional))


def counts(v,keys):
    need(all(count(v[k]) for k in keys))


def count_map(v,allowed=None):
    need(type(v) is dict and all(type(k) is str and k and count(n) for k,n in v.items()))
    if allowed is not None:need(set(v)<=set(allowed))
    return sum(v.values())


def digest(v):need(type(v) is str and len(v)==64 and all(c in '0123456789abcdef' for c in v))

def decision_id(v):return type(v) is str and len(v)==32 and all(c in '0123456789abcdef' for c in v)


def facts(v,total=None):
    need(FACT_KEYS<=set(v));counts(v,('fact_count','diagnostic_sample_count'))
    n=v['fact_count'];sample=v['facts']
    need(type(sample) is list and len(sample)==min(8,n)==v['diagnostic_sample_count']
         and all(type(f) is dict for f in sample) and v['diagnostic_sample_non_inferential'] is True
         and v['diagnostic_sample_rule']=='first_eight_in_source_order')
    digest(v['facts_sha256'])
    if total is not None:need(n==total)
    if n<=8:
        raw=json.dumps(sample,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
        need(v['facts_sha256']==hashlib.sha256(b'SEED_B10_AUDIT_FACTS_V1\0'+raw).hexdigest())
    return sample,n


def summary(v,key,sample,total,predicate):
    counts(v,(key,));observed=sum(predicate(f) for f in sample)
    need(observed<=v[key]<=observed+total-len(sample))


def support(v,total):
    need(type(v) is dict)
    if 'encoding' not in v:
        need(count_map(v)==total and all(k=='unavailable' or k.isdecimal() and str(int(k))==k for k in v))
    else:
        shape(v,('encoding','ranges','unavailable'));counts(v,('unavailable',))
        need(v['encoding']=='inclusive_support_ranges_with_count' and type(v['ranges']) is list)
        previous=-1;n=v['unavailable']
        for r in v['ranges']:
            need(type(r) is list and len(r)==3 and all(count(x) for x in r) and r[0]>previous and r[1]>=r[0] and r[2]>0)
            previous=r[1];n+=(r[1]-r[0]+1)*r[2]
        need(n==total)


def adaptation(value,d):
    keys=('observed_rest_exposures','observed_postshift_transitions','paired_usable_rest_samples','registered_postshift_transition_horizon')
    counts(d,keys);n=d['observed_rest_exposures'];usable=d['paired_usable_rest_samples']
    need(usable<=n<=d['observed_postshift_transitions']<=480 and d['registered_postshift_transition_horizon']==480)
    need(d['rest_coverage'] is None if n==0 else close(d['rest_coverage'],usable/n))
    losses=d['first_five_rest_exposure_losses'];need(type(losses) is list and len(losses)==min(5,n))
    need(all(x is None or number(x) and x>=0 for x in losses))
    if n:
        need(type(d['first_postshift_rest_ordinal']) is int and 321<=d['first_postshift_rest_ordinal']<=800
             and same(d['first_postshift_rest_loss'],losses[0]))
    else:need(d['first_postshift_rest_ordinal'] is None and d['first_postshift_rest_loss'] is None)
    candidate=d['prechange_candidate'];need(type(candidate) is dict)
    if value is None:return
    need(candidate.get('method')=='action_mean_delta' and candidate.get('status')=='predicted'
         and type(candidate.get('evidence_count')) is int and candidate['evidence_count']>=2)
    windows=d['exposure_windows'];need(type(windows) is list)
    previous=320;passing=[];qualified=[];first_success=None;eligible=False
    for i,w in enumerate(windows):
        shape(w,('start_exposure','end_exposure','end_ordinal','paired_count','mae','status'))
        need(type(w['end_ordinal']) is int and previous<w['end_ordinal']<=800
             and type(w['start_exposure']) is int and w['start_exposure']==i*5+1
             and type(w['end_exposure']) is int and w['end_exposure']==i*5+5<=n
             and count(w['paired_count']) and w['paired_count']<=5)
        previous=w['end_ordinal'];q=w['paired_count']==5
        need(w['status']==('qualified' if q else 'unavailable'))
        need(number(w['mae']) and w['mae']>=0 if q else w['mae'] is None)
        qualified=qualified+[w] if q else [];eligible|=len(qualified)>=3
        passing=passing+[w] if q and w['mae']<=.02 else []
        if len(passing)>=3 and first_success is None:first_success=passing[-3:]
    need(eligible)
    if value['event']=='observed':
        shape(value,('event','rest_exposures','completed_transition_delay','confirmation_windows'))
        need(first_success is not None and same(value['confirmation_windows'],first_success)
             and count(value['rest_exposures']) and value['rest_exposures']==first_success[-1]['end_exposure']
             and count(value['completed_transition_delay']) and value['completed_transition_delay']==first_success[-1]['end_ordinal']-320
             and windows[-1]==first_success[-1])
    else:
        shape(value,('event','right_censored_rest_exposures','right_censored_completed_transitions','registered_postshift_transition_horizon'))
        need(value['event']=='not_observed' and first_success is None and len(windows)==n//5)
        counts(value,('right_censored_rest_exposures','right_censored_completed_transitions','registered_postshift_transition_horizon'))
        need(value['right_censored_rest_exposures']==n and value['registered_postshift_transition_horizon']==480
             and d['observed_postshift_transitions']<=value['right_censored_completed_transitions']<=480
             and value['right_censored_completed_transitions']>=previous-320)


def world(metric,v,d):
    if metric in ('world.evidence-count','world.insufficient-evidence'):
        shape(v,('published','pending','beliefs' if metric.endswith('evidence-count') else 'published_evidence_available'))
        counts(v,('published',));need(v['pending'] is None or count(v['pending']))
        if metric.endswith('evidence-count'):
            need(type(v['beliefs']) is dict and len(v['beliefs'])==v['published']
                 and all(type(k) is str and k and type(n) is int and n>=2 for k,n in v['beliefs'].items()))
        else:need(type(v['published_evidence_available']) is bool and v['published_evidence_available']==bool(v['published']))
    elif metric=='world.first-belief':
        shape(v,('first_publication_ordinal','belief_key','source_transition_id'))
        need(positive(v['first_publication_ordinal']) and positive(v['source_transition_id']) and type(v['belief_key']) is str and bool(v['belief_key']))
    elif metric=='world.revision-latency':
        shape(v,('first_changed_rest_ordinal','revision_ordinal','rest_exposure_transition_latency'))
        need(positive(v['first_changed_rest_ordinal']) and positive(v['revision_ordinal']) and count(v['rest_exposure_transition_latency'])
             and v['rest_exposure_transition_latency']==v['revision_ordinal']-v['first_changed_rest_ordinal'])
    else:
        shape(v,('beliefs',));need(type(v['beliefs']) is dict)
        for k,b in v['beliefs'].items():
            need(type(k) is str and bool(k))
            if metric=='world.stability':
                shape(b,('mean_absolute_change','revisions'))
                need(number(b['mean_absolute_change']) and b['mean_absolute_change']>=0 and positive(b['revisions']))
            else:
                shape(b,('count','evidence_count','scope','scope_value','mean_delta','probability_true','confidence','confidence_reference','confidence_matches','first_transition_id','last_transition_id'))
                need(count(b['count']) and type(b['evidence_count']) is int and 2<=b['evidence_count'] and b['count']<=b['evidence_count'])
                need(b['scope']=='global' and b['scope_value']=='' or b['scope']=='action' and b['scope_value'] in ACTIONS)
                need(b['mean_delta'] is None or number(b['mean_delta']))
                need(b['probability_true'] is None or number(b['probability_true']) and 0<=b['probability_true']<=1)
                need(number(b['confidence']) and 0<=b['confidence']<=1 and close(b['confidence_reference'],min(.95,b['evidence_count']/20)*(1-b['count']/b['evidence_count'])))
                need(type(b['confidence_matches']) is bool and b['confidence_matches']==close(b['confidence'],b['confidence_reference']))
                need(positive(b['first_transition_id']) and positive(b['last_transition_id']) and b['first_transition_id']<=b['last_transition_id'])
        if metric=='world.stability':need(positive(d['revisions']) and d['revisions']==sum(b['revisions'] for b in v['beliefs'].values()))


def curiosity(metric,v):
    if metric!='curiosity.components':
        key='violations' if metric=='curiosity.bounds' else 'unavailable'
        shape(v,(key,'assessments'));counts(v,(key,'assessments'))
        need(v['assessments']>0 and v[key]<=v['assessments']);return
    keys=('formula_matches','assessments','source_matches','source_mismatches','source_unavailable',
          'b3_source_matches','b3_source_mismatches','b3_source_unavailable','prior_source_mismatches','prior_source_unavailable')
    shape(v,(*keys,*FACT_KEYS));counts(v,keys);sample,n=facts(v,v['assessments']);need(n>0)
    need(v['source_matches']+v['source_mismatches']+v['source_unavailable']==n
         and v['b3_source_matches']+v['b3_source_mismatches']+v['b3_source_unavailable']==n)
    for f in sample:
        need(positive(f['transition_id']) and f['source_status'] in ('MATCH','MISMATCH','UNAVAILABLE')
             and f['prior_source_status'] in ('captured','unavailable'))
        need(all(f[k] is None or type(f[k]) is bool for k in ('matches','b3_source_matches')))
        for k in ('actual_score','reference_score','prediction_surprise','coverage','uncertainty','novelty','b3_reference_surprise'):
            need(f[k] is None or number(f[k]) and 0<=f[k]<=1)
        need(type(f['source_mismatched_fields']) is list and type(f['source_missing']) is list and type(f['prior_source_checks']) is list)
        need(all(type(c['matches']) is bool and (c['contradiction_matches'] is None or type(c['contradiction_matches']) is bool) for c in f['prior_source_checks']))
    summary(v,'formula_matches',sample,n,lambda f:f['matches'] is True)
    for key,status in (('matches','MATCH'),('mismatches','MISMATCH'),('unavailable','UNAVAILABLE')):
        summary(v,'source_'+key,sample,n,lambda f:f['source_status']==status)
    for key,answer in (('matches',True),('mismatches',False),('unavailable',None)):
        summary(v,'b3_source_'+key,sample,n,lambda f:f['b3_source_matches'] is answer)
    summary(v,'prior_source_unavailable',sample,n,lambda f:f['prior_source_status']=='unavailable')
    prior=sum(c['matches'] is False or c['contradiction_matches'] is False for f in sample for c in f['prior_source_checks'])
    need(v['prior_source_mismatches']>=prior)
    if n<=8:need(v['prior_source_mismatches']==prior)


def semantic(metric,v,d):
    if metric=='semantic.revisions':
        shape(v,('revisions','semantic_ids'));counts(v,('revisions',))
        ids=v['semantic_ids'];need(type(ids) is list and all(positive(i) for i in ids) and ids==sorted(set(ids)) and len(ids)<=v['revisions'] and bool(ids)==bool(v['revisions']));return
    if metric=='semantic.promotion-latency':
        inventory_keys=('expected_examined_opportunities','validated_actual_eligible_opportunities','opportunity_inventory_count','scoped_opportunity_count','scope_exclusion_count','validated_scoped_eligible_opportunities','scope_exclusion_counts')
        shape(v,('promotions','eligible_opportunities','exclusions',*FACT_KEYS,*inventory_keys));counts(v,('eligible_opportunities',*inventory_keys[:-1]));count_map(v['exclusions'])
        need(v['scoped_opportunity_count']+v['scope_exclusion_count']==v['opportunity_inventory_count']
             and count_map(v['scope_exclusion_counts'],('action','signal'))==v['scope_exclusion_count']
             and v['validated_actual_eligible_opportunities']<=v['expected_examined_opportunities']
             and v['eligible_opportunities']==v['validated_scoped_eligible_opportunities']<=v['validated_actual_eligible_opportunities']
             and v['eligible_opportunities']<=v['scoped_opportunity_count'])
        sample,n=facts(v);promotions=v['promotions'];need(type(promotions) is list and len(promotions)<=v['eligible_opportunities']<=n)
        seen=set();events=set();sources=set()
        for p in promotions:
            shape(p,('source_belief_id','run_id','semantic_memory_id','creation_event_id','revision','source_fingerprint','eligible_at','published_at','latency'))
            need(all(positive(p[k]) for k in ('source_belief_id','run_id','semantic_memory_id','creation_event_id')) and type(p['revision']) is int and p['revision']==1)
            digest(p['source_fingerprint']);need(number(p['eligible_at']) and number(p['published_at']) and number(p['latency']) and p['latency']>=0 and close(p['latency'],p['published_at']-p['eligible_at']))
            identity=(p['run_id'],p['source_belief_id']);need(p['semantic_memory_id'] not in seen and p['creation_event_id'] not in events and identity not in sources)
            seen.add(p['semantic_memory_id']);events.add(p['creation_event_id']);sources.add(identity)
        for f in sample:
            need(positive(f['run_id']) and positive(f['source_belief_id']) and number(f['eligible_at']) and count(f['actual_run_eligible_beliefs']) and f['source_status'] in ('MATCH','MISMATCH','UNAVAILABLE'))
            if f['source_status']!='UNAVAILABLE':
                need(count(f['reference_support']) and number(f['reference_confidence']) and 0<=f['reference_confidence']<=1);digest(f['source_fingerprint'])
        expected=sum(f['source_status']=='MATCH' and f['actual_run_eligible_beliefs']>0 and f['reference_support']>=8 and f['reference_confidence']>=.30 for f in sample)
        need(expected<=v['eligible_opportunities']<=expected+n-len(sample))
        return
    if metric=='semantic.status-transitions':
        keys=('current_status_counts','historical_status_counts','revision_edges','status_changes','unchanged_status_revisions','reactivations','status_transition_counts','reactivation_requires_observed_prior_active')
        shape(v,(*keys,*FACT_KEYS));sample,n=facts(v,v['revision_edges']);counts(v,('revision_edges','status_changes','unchanged_status_revisions','reactivations'))
        for key in ('current_status_counts','historical_status_counts'):count_map(v[key],('active','weakened','source_unavailable'))
        need(count(d['denominator']) and d['denominator']==n and v['status_changes']+v['unchanged_status_revisions']==n
             and v['reactivations']<=v['status_changes'] and v['reactivation_requires_observed_prior_active'] is True
             and count_map(v['status_transition_counts'])==v['status_changes'])
        states=('active','weakened','source_unavailable')
        need(all(k in {a+'->'+b for a in states for b in states if a!=b} for k in v['status_transition_counts']))
        for f in sample:
            need(positive(f['semantic_id']) and positive(f['from_revision']) and positive(f['to_revision']) and f['to_revision']==f['from_revision']+1
                 and f['from_status'] in states and f['to_status'] in states and type(f['reactivation']) is bool)
            if f['reactivation']:need(f['from_status']!='active' and f['to_status']=='active')
        summary(v,'status_changes',sample,n,lambda f:f['from_status']!=f['to_status'])
        summary(v,'reactivations',sample,n,lambda f:f['reactivation'])
        if n<=8:
            for key,total in v['status_transition_counts'].items():need(total==sum(f['from_status']+'->'+f['to_status']==key for f in sample))
        return
    keys=('matched','valid_source_links','content_matched','content_mismatched','content_unavailable','cursor','opportunities')
    shape(v,(*keys,*FACT_KEYS));sample,n=facts(v);counts(v,keys[:5]);need(v['opportunities'] is None or count(v['opportunities']))
    need(v['cursor'] is None or type(v['cursor']) is list and all(type(r) is dict for r in v['cursor']))
    need(v['content_matched']+v['content_mismatched']+v['content_unavailable']==n)
    for f in sample:
        need(positive(f['semantic_id']) and positive(f['source_belief_id']) and f['status'] in ('active','weakened','source_unavailable') and f['content_status'] in ('MATCH','MISMATCH','UNAVAILABLE'))
        need(all(type(f[k]) is bool for k in ('source_available','fingerprint_matches','source_unavailable_consistent','source_link_valid','claimed_eligible')))
        need(type(f['content_mismatched_fields']) is list)
    summary(v,'matched',sample,n,lambda f:f['fingerprint_matches'])
    summary(v,'valid_source_links',sample,n,lambda f:f['source_link_valid'])
    for key,status in (('matched','MATCH'),('mismatched','MISMATCH'),('unavailable','UNAVAILABLE')):
        summary(v,'content_'+key,sample,n,lambda f:f['content_status']==status)


def session(v):
    if v['status']=='MEASURED':shape(v,('status','matches'));need(type(v['matches']) is bool)
    else:shape(v,('status','reason'));need(v['status']=='UNAVAILABLE' and v['reason']=='MISSING_PUBLICATION_SESSION_SOURCE')


def self_model(metric,v,d):
    # Original producer-invalid snapshot is itself measured negative evidence.
    if v=={'unsupported':1,'claims':[{'path':'snapshot','reason':'invalid_producer_contract'}]}:
        need(type(v['unsupported']) is int and type(d['denominator']) is int and d['denominator']==1);return
    if metric=='self.freshness':
        shape(v,('status_counts','stale','basis','source_faithful','session_audit','built_at','read_at'))
        counts(v,('stale',));need(count_map(v['status_counts'])==d['denominator'] and count(d['denominator']) and v['stale']==v['status_counts'].get('stale',0))
        need(v['basis']=='producer_claim_projection' and type(v['source_faithful']) is bool and number(v['built_at']) and number(v['read_at']));session(v['session_audit']);return
    keys=('unsupported','claims','session_audit')
    shape(v,keys if metric=='self.unsupported-claims' else (*keys,'checked','supported'));counts(v,('unsupported',));session(v['session_audit'])
    claims=v['claims'];need(type(claims) is list and count(d['denominator']) and v['unsupported']<=d['denominator'])
    seen=set()
    for c in claims:
        shape(c,('path','supported','actual','expected','reference_checks'),('reference_conflicts',))
        need(type(c['path']) is str and c['path'] and c['path'] not in seen and type(c['supported']) is bool and positive(c['reference_checks']));seen.add(c['path'])
        conflicts=c.get('reference_conflicts',[]);need(type(conflicts) is list and len(conflicts)<c['reference_checks'])
        supported=same(c['actual'],c['expected'])
        for f in conflicts:
            shape(f,('actual','expected','supported'));need(type(f['supported']) is bool and f['supported']==same(f['actual'],f['expected']));supported&=f['supported']
        need(c['supported']==supported)
    need(v['unsupported']==sum(c['supported'] is False for c in claims))
    if metric=='self.unsupported-claims':need(len(claims)==v['unsupported'])
    else:
        counts(v,('checked','supported'));need(v['checked']==len(claims)==d['denominator'] and v['supported']+v['unsupported']==v['checked'])


def decision(metric,v,d):
    denominator=d['denominator'];need(count(denominator))
    if metric in ('decision.constraints','decision.prediction-link'):
        key='violations' if metric=='decision.constraints' else 'matched';shape(v,(key,'checked'));counts(v,(key,'checked'))
        need(0<=v[key]<=v['checked']==denominator and denominator>0);return
    if metric=='decision.skipped-fallback':
        keys=('skipped_attempts','fallback','completed_decisions','skipped_reasons','skipped_source_status','skipped_source_reason')
        extra=('attempt_inventory_count','excluded_attempt_count','excluded_attempt_counts','scoped_attempt_count','attempt_inventory_sha256')
        shape(v,keys,extra);counts(v,('fallback','completed_decisions'));need(v['fallback']<=v['completed_decisions']==denominator)
        if v['skipped_source_status']=='MEASURED':
            need(count(v['skipped_attempts']) and count_map(v['skipped_reasons'])==v['skipped_attempts'] and v['skipped_source_reason'] is None)
        else:need(v['skipped_source_status']=='UNAVAILABLE' and v['skipped_attempts'] is None and v['skipped_reasons'] is None and type(v['skipped_source_reason']) is str and bool(v['skipped_source_reason']))
        if set(extra)&set(v):
            need(set(extra)<=set(v));counts(v,('attempt_inventory_count','excluded_attempt_count'));digest(v['attempt_inventory_sha256'])
            need(count_map(v['excluded_attempt_counts'])==v['excluded_attempt_count']<=v['attempt_inventory_count'])
            if v['skipped_source_status']=='MEASURED':need(count(v['scoped_attempt_count']) and v['scoped_attempt_count']==v['skipped_attempts'] and v['scoped_attempt_count']+v['excluded_attempt_count']==v['attempt_inventory_count'])
            else:need(v['scoped_attempt_count'] is None)
        return
    if metric=='decision.q-compatibility':
        shape(v,('matched','mismatched','missing_source_updates',*FACT_KEYS));counts(v,('matched','mismatched','missing_source_updates'));sample,n=facts(v)
        need(v['matched']+v['mismatched']==denominator>0 and denominator+v['missing_source_updates']==n)
        for f in sample:
            need(decision_id(f['decision_id']) and f['source_status'] in ('MEASURED','UNAVAILABLE'))
            if f['source_status']=='MEASURED':
                need(type(f['matches']) is bool and positive(f['transition_id']) and type(f['source_links']) is dict and all(type(x) is bool for x in f['source_links'].values()) and number(f['expected_value']) and number(f['actual_value']) and count(f['actual_visits']))
                if f['matches']:need(all(f['source_links'].values()) and close(f['expected_value'],f['actual_value']))
            else:need(f['matches'] is None and f['reason']=='MISSING_OR_INVALID_Q_UPDATE_SOURCE')
        summary(v,'matched',sample,n,lambda f:f['matches'] is True)
        summary(v,'mismatched',sample,n,lambda f:f['matches'] is False)
        summary(v,'missing_source_updates',sample,n,lambda f:f['source_status']=='UNAVAILABLE');return
    keys=('structurally_valid','checked_candidates','matched','mismatched') if metric=='decision.eligibility' else (
        'structurally_valid','q_source_checked_candidates','q_source_matched_candidates','q_source_mismatched_candidates','q_source_unavailable_candidates')
    shape(v,(*keys,*FACT_KEYS));counts(v,keys);sample,n=facts(v,v['structurally_valid']);need(n>0)
    checks=[]
    for f in sample:
        need(decision_id(f['decision_id']) and positive(f['ordinal']) and f['action'] in ACTIONS and f['selection_mode'] in ('exploit','explore','fallback'))
        digest(f['completed_evidence_sha256']);digest(f['selected_prediction_sha256'])
        need(type(f['prediction_link_matches']) is bool and type(f['guard_checks']) is dict and set(f['guard_checks'])==set(ACTIONS)
             and type(f['q_source_checks']) is dict and set(f['q_source_checks'])==set(ACTIONS))
        guard=metric=='decision.eligibility'
        for c in (f['guard_checks'] if guard else f['q_source_checks']).values():
            need(type(c['matches']) is bool if guard else c['matches'] is None or type(c['matches']) is bool)
            if guard:
                need(type(c['actual_eligible']) is bool and type(c['actual_reasons']) is list and type(c['expected_reasons']) is list)
                need(c['matches']==(same(c['actual_reasons'],c['expected_reasons']) and c['actual_eligible']==(not c['expected_reasons'])))
            else:
                need(c['status'] in ('MEASURED','UNAVAILABLE'))
                need(c['matches'] is None and c['expected'] is None if c['status']=='UNAVAILABLE' else type(c['matches']) is bool and c['matches']==same(c['actual'],c['expected']))
            checks.append(c)
    if metric=='decision.eligibility':
        need(v['checked_candidates']==denominator==4*n and v['matched']+v['mismatched']==4*n)
        summary(v,'matched',checks,4*n,lambda c:c['matches'])
        summary(v,'mismatched',checks,4*n,lambda c:not c['matches'])
    else:
        need(denominator==n and v['q_source_checked_candidates']+v['q_source_unavailable_candidates']==4*n and v['q_source_matched_candidates']+v['q_source_mismatched_candidates']==v['q_source_checked_candidates'])
        for key,predicate in (('checked',lambda c:c['status']=='MEASURED'),('unavailable',lambda c:c['status']=='UNAVAILABLE'),('matched',lambda c:c['matches'] is True),('mismatched',lambda c:c['matches'] is False)):
            summary(v,'q_source_'+key+'_candidates',checks,4*n,predicate)


def valid_structured(row,d):
    v=row.value;need(type(v) is dict)
    metric=row.metric
    if metric=='prediction.coverage':need(same(v,d['coverage']))
    elif metric=='prediction.support-counts':
        shape(v,('methods','support'));need(same(v['methods'],d['methods']) and same(v['support'],d['method_support']))
        need(count_map(v['methods'])==d['opportunities']);support(v['support'],d['opportunities'])
    elif metric=='prediction.adaptation-delay':adaptation(v,d)
    elif metric.startswith('world.'):world(metric,v,d)
    elif metric.startswith('curiosity.'):curiosity(metric,v)
    elif metric.startswith('semantic.'):semantic(metric,v,d)
    elif metric.startswith('self.'):self_model(metric,v,d)
    elif metric.startswith('decision.'):decision(metric,v,d)
    else:need(False)
    return True
