"""Immutable plan admission and durable freeze. Scientific dispatch disabled."""
import hashlib
import os
from .canonical import canonical_bytes
from .contracts import AnalysisPlan, FrozenPlan, Measurement, ContractError, fields, strict_json, validate_json
from .registry import lookup, PROTOCOLS, ACTIONS, METRICS, REGISTRIES
from .specs import identifier, integer, versions, seeds, windows, raw_bytes

PLAN_FIELDS = ('schema', 'experiment_id', 'experiment_version', 'analysis_plan_version', 'members',
               'metrics', 'seeds', 'populations', 'windows', 'baselines', 'exclusions', 'eligibility',
               'coverage', 'aggregation', 'standardization', 'missing_rules', 'thresholds', 'questions', 'exploratory')


def validate_plan(raw) -> AnalysisPlan:
    validate_json(raw)
    fields(raw, PLAN_FIELDS, ('inventory_profiles',))
    if raw['schema'] != 'b10_analysis_plan_v1':
        raise ContractError()
    identifier(raw['experiment_id'])
    integer(raw['experiment_version'])
    integer(raw['analysis_plan_version'])
    seeds(raw['seeds'])
    versions(raw['metrics'], 'metric')
    versions(raw['baselines'], 'baseline', 2)
    windows(raw['windows'])
    if type(raw['members']) is not list or not 1 <= len(raw['members']) <= 32:
        raise ContractError()
    seen = set()
    for m in raw['members']:
        fields(m, ('id', 'family', 'scenario_version', 'rule_version', 'protocol', 'variant', 'seed', 'training', 'measured'), ('profile',))
        identifier(m['id'])
        lookup(m['family'], m['scenario_version'], kind='family')
        integer(m['rule_version'])
        integer(m['seed'], 0, 2**63-1)
        integer(m['training'], 0, 512)
        integer(m['measured'], 1, 1024)
        if (m['id'] in seen or m['seed'] not in raw['seeds'] or m['rule_version'] != m['scenario_version']
                or m['training'] + m['measured'] > 1024 or m['protocol'] not in PROTOCOLS
                or m['variant'] not in ('seed', 'random-eligible', 'fresh', 'contradictory', 'unavailable', 'stale')):
            raise ContractError()
        seen.add(m['id'])
    if type(raw['populations']) is not list or not raw['populations']:
        raise ContractError()
    ids = set()
    for p in raw['populations']:
        fields(p, ('id', 'phase', 'action', 'signal'), ('method', 'comparison', 'stratum', 'variant'))
        identifier(p['id'])
        if p['id'] in ids or p['phase'] not in ('training', 'measured', 'probe') or p['action'] not in ('all', 'observe', 'reflect', 'consolidate', 'rest') or p['signal'] not in ('all', 'battery_pct', 'load_ratio', 'disk_free_pct', 'network'):
            raise ContractError()
        ids.add(p['id'])
        if (p.get('method', 'seed') not in ('seed', 'persistence', 'global-history')
                or p.get('comparison') not in (None, 'persistence', 'global-history')
                or p.get('stratum', 'all_methods') not in ('all_methods', 'action_mean')):
            raise ContractError()
        if p.get('variant') not in (None,'fresh','contradictory','unavailable','stale'):
            raise ContractError()
    fixed = {'eligibility': 'registered_support', 'coverage': 'all_opportunities', 'aggregation': 'ordered_fsum',
             'standardization': 'equal_qualifying_actions', 'missing_rules': 'unavailable_with_reason'}
    if any(raw[k] != v for k, v in fixed.items()) or type(raw['exploratory']) is not bool:
        raise ContractError()
    if type(raw['exclusions']) is not list or any(v not in ('invalid_observation', 'insufficient_support', 'not_applicable') for v in raw['exclusions']):
        raise ContractError()
    if type(raw['thresholds']) is not list or type(raw['questions']) is not list or not raw['questions']:
        raise ContractError()
    tids = set()
    for t in raw['thresholds']:
        fields(t, ('id', 'version', 'value', 'metric', 'metric_version', 'population', 'direction', 'role', 'rationale', 'missing_rule'))
        identifier(t['id'])
        integer(t['version'])
        lookup(t['metric'], t['metric_version'], kind='metric')
        if (t['id'] in tids or type(t['value']) not in (int, float) or t['population'] not in ids
                or t['direction'] not in ('le', 'ge', 'eq') or t['role'] not in ('eligibility', 'event', 'engineering', 'classification')
                or type(t['rationale']) is not str or not t['rationale'] or t['missing_rule'] not in ('unavailable', 'inconclusive')):
            raise ContractError()
        tids.add(t['id'])
    qids = set()
    for q in raw['questions']:
        fields(q, ('id', 'metrics', 'rule', 'reason'), ('thresholds',))
        identifier(q['id'])
        if q['id'] in qids or type(q['metrics']) is not list or not q['metrics'] or len(set(q['metrics'])) != len(q['metrics']) or set(q['metrics']) - {m['id'] for m in raw['metrics']}:
            raise ContractError()
        descriptive=q['rule']=='descriptive_only' and q['reason']=='DESCRIPTIVE_ONLY_NO_CLASSIFICATION_RULE' and 'thresholds' not in q
        classified=q['rule']=='thresholds_v1' and q['reason']=='PREREGISTERED_THRESHOLD_RULE'
        if classified:
            references=q.get('thresholds')
            if (type(references) is not list or not references or len(set(references))!=len(references)
                    or any(ref not in tids for ref in references)):
                raise ContractError()
            chosen=[t for t in raw['thresholds'] if t['id'] in references]
            if any(t['role']!='classification' or t['metric'] not in q['metrics'] or t['missing_rule']!='inconclusive' for t in chosen):
                raise ContractError()
        if not descriptive and not classified:
            raise ContractError()
        qids.add(q['id'])
    profiles=raw.get('inventory_profiles',[])
    if type(profiles) is not list or len(profiles)>8:
        raise ContractError()
    profile_ids=set()
    metric_ids={m['id'] for m in raw['metrics']}
    window_ids={w['id'] for w in raw['windows']}
    for profile in profiles:
        fields(profile,('id','family','protocol','metric_populations','metric_windows','exploratory'))
        identifier(profile['id'])
        if profile['id'] in profile_ids or profile['family'] not in ('A','B','C','D') or profile['protocol'] not in PROTOCOLS:
            raise ContractError()
        profile_ids.add(profile['id'])
        for key,allowed in (('metric_populations',ids),('metric_windows',window_ids)):
            mapping=profile[key]
            if type(mapping) is not dict or set(mapping)!=metric_ids:
                raise ContractError()
            for references in mapping.values():
                if type(references) is not list or not references or len(set(references))!=len(references) or set(references)-allowed:
                    raise ContractError()
        if type(profile['exploratory']) is not list or len(profile['exploratory'])>32 or (profile['exploratory'] and not raw['exploratory']):
            raise ContractError()
        for extra in profile['exploratory']:
            fields(extra,('metric','population','window'))
            if extra['metric'] not in metric_ids or extra['population'] not in ids or extra['window'] not in window_ids:
                raise ContractError()
    for member in raw['members']:
        if profiles:
            profile=next((p for p in profiles if p['id']==member.get('profile')),None)
            if profile is None or profile['family']!=member['family'] or profile['protocol']!=member['protocol']:
                raise ContractError()
        elif 'profile' in member:
            raise ContractError()
    body = raw_bytes(raw)
    if len(canonical_bytes(raw)) > 128*1024:
        raise ContractError()
    plan = AnalysisPlan(body)
    expand_inventory(plan)
    return plan


def expand_inventory(plan):
    p = strict_json(plan.body, max_bytes=128*1024)
    results = []
    # Budget admission precedes the allocation of each inventory row.
    total_bytes=0
    for member in p['members']:
        byte_count = 2
        member_count = 0
        profile=next((x for x in p.get('inventory_profiles',[]) if x['id']==member.get('profile')),None)
        def entries():
            for metric in p['metrics']:
                populations=p['populations'] if profile is None else [x for x in p['populations'] if x['id'] in profile['metric_populations'][metric['id']]]
                selected_windows=p['windows'] if profile is None else [x for x in p['windows'] if x['id'] in profile['metric_windows'][metric['id']]]
                for population in populations:
                    for window in selected_windows:
                        yield metric,population,window,'PRIMARY'
            if profile:
                for extra in profile['exploratory']:
                    yield (next(m for m in p['metrics'] if m['id']==extra['metric']),
                        next(x for x in p['populations'] if x['id']==extra['population']),
                        next(x for x in p['windows'] if x['id']==extra['window']),'EXPLORATORY_DIAGNOSTIC')
        seen=set()
        for metric,population,window,role in entries():
            identity = ':'.join([member['id'], metric['id'], population['id'], window['id']])
            if role=='EXPLORATORY_DIAGNOSTIC':identity+='~exploratory'
            if identity in seen:raise ContractError()
            seen.add(identity)
            meta=inventory_metadata(member,metric['id'],population,window,role)
            row = Measurement(identity, metric['id'], metric['version'], member['id'],
                              'UNAVAILABLE' if meta['applicable'] else 'NOT_EVALUATED',raw_bytes(meta),role)
            byte_count += len(raw_bytes({'id':identity,'metric':row.metric,'version':row.version,'member':row.member,
                                        'role':role,'state':row.state,'value':None,**meta})) + 1
            if byte_count > 256*1024 or member_count >= 4096:
                raise ContractError()
            results.append(row)
            member_count += 1
        total_bytes+=byte_count
    # Attempt and plan/control inventories share the 4 MiB ceiling.
    if total_bytes + len(plan.body) + 2048*512 > 4*1024**2:
        raise ContractError()
    return tuple(results)


def inventory_metadata(member,metric,population,window,role='PRIMARY'):
    family,protocol=member['family'],member['protocol']
    signal=population['signal']
    applicable=True
    if metric=='prediction.adaptation-delay':applicable=family=='B' and protocol=='PREQUENTIAL'
    elif metric=='decision.task-utility':applicable=family=='D' and protocol=='PREQUENTIAL'
    elif metric=='prediction.window-change':applicable=family in ('A','B') and protocol=='PREQUENTIAL'
    elif metric in ('world.first-belief','world.revision-latency','world.stability','semantic.promotion-latency','semantic.revisions','semantic.status-transitions'):
        applicable=protocol=='PREQUENTIAL'
    if metric in ('prediction.numeric-mae','prediction.numeric-normalized-mae','prediction.window-change'):
        applicable &= signal in ('battery_pct','load_ratio','disk_free_pct')
    elif metric in ('prediction.boolean-accuracy','prediction.boolean-brier'):
        applicable &= signal=='network'
        if metric=='prediction.boolean-brier' and (population.get('method')=='persistence' or population.get('comparison')=='persistence'):
            applicable=False
    dimensions=dict(family=family,protocol=protocol,seed=member['seed'],population=population['id'],window=window['id'],
        phase=population['phase'],action=population['action'],signal=signal,method=population.get('method','seed'),
        comparison=population.get('comparison'),stratum=population.get('stratum','all_methods'),
        variant=population.get('variant',member['variant']),action_strata=list(ACTIONS),
        window_start=window['start'],window_end=window['end'],window_unit=window['unit'])
    return dict(dimensions=dimensions,applicable=bool(applicable),non_inferential=role=='EXPLORATORY_DIAGNOSTIC',
                reason=None if applicable else 'NOT_APPLICABLE_TO_REGISTERED_PROTOCOL_OR_FAMILY')


def default_plan() -> AnalysisPlan:
    """Checked-in preregistration factory. Constructing it executes nothing."""
    populations=[]
    def group(prefix,phase,variant=None,sparse=False):
        result={}
        for signal,label in (('battery_pct','battery'),('load_ratio','load'),('disk_free_pct','disk'),('network','network'),('all','facts')):
            modes=('seed',) if sparse or signal=='all' else ('seed','persistence','global','paired-persistence','paired-global')
            if signal=='load_ratio' and not sparse:modes+=('conditioned-global',)
            for mode in modes:
                identity=prefix+'-'+label+'-'+mode
                method='persistence' if mode=='persistence' else 'global-history' if mode=='global' else 'seed'
                comparison='persistence' if mode=='paired-persistence' else 'global-history' if mode in ('paired-global','conditioned-global') else None
                pop=dict(id=identity,phase=phase,action='all',signal=signal,method=method,comparison=comparison,
                         stratum='action_mean' if mode=='conditioned-global' else 'all_methods')
                if variant is not None:pop['variant']=variant
                populations.append(pop);result[(signal,mode)]=identity
        return result
    online=group('online','measured')
    held=group('held','probe')
    robustness=[group('c-'+variant,'probe',variant,sparse=True) for variant in ('fresh','contradictory','unavailable','stale')]
    window_definitions=[('a-whole',1,400),('a-early',1,40),('a-late',361,400),('a-heldout',1,80),
        ('b-whole',1,800),('b-pre',281,320),('b-immediate',321,360),('b-late',761,800),
        ('c-probes',1,16),('d-whole',1,128)]
    profiles=[]
    for identity,family,protocol,groups,whole,point_windows in (
            ('a-online','A','PREQUENTIAL',[online],'a-whole',['a-whole','a-early','a-late']),
            ('a-frozen','A','FROZEN_SELECTION_ASSAY',[held],'a-heldout',['a-heldout']),
            ('b-online','B','PREQUENTIAL',[online],'b-whole',['b-whole','b-pre','b-immediate','b-late']),
            ('c-frozen','C','FROZEN_SELECTION_ASSAY',robustness,'c-probes',['c-probes']),
            ('d-online','D','PREQUENTIAL',[online],'d-whole',['d-whole'])):
        mapping={metric:[] for metric in METRICS}
        metric_windows={metric:[whole] for metric in METRICS}
        metric_windows['prediction.numeric-mae']=point_windows
        for g in groups:
            numeric=[p for (s,mode),p in g.items() if s in ('battery_pct','load_ratio','disk_free_pct') and mode!='conditioned-global']
            network=[p for (s,mode),p in g.items() if s=='network']
            mapping['prediction.numeric-mae']+=numeric
            mapping['prediction.numeric-normalized-mae']+=numeric
            mapping['prediction.boolean-accuracy']+=network
            mapping['prediction.boolean-brier'] += [p for (s,mode),p in g.items() if s=='network' and mode not in ('persistence','paired-persistence')]
            mapping['prediction.coverage'] += [p for (s,mode),p in g.items() if s!='all' and mode in (('seed',) if family=='C' else ('paired-global','paired-persistence'))]
            mapping['prediction.support-counts'] += [p for (s,mode),p in g.items() if s!='all' and mode=='seed']
            mapping['prediction.window-change'] += [p for (s,mode),p in g.items() if s=='load_ratio' and mode in (('seed',) if family=='C' else ('paired-global','paired-persistence','conditioned-global'))]
            mapping['prediction.adaptation-delay'].append(g[('load_ratio','seed')])
            for metric in METRICS:
                if not metric.startswith('prediction.'):mapping[metric].append(g[('all','seed')])
        exploratory=[]
        if family in ('A','B') and protocol=='PREQUENTIAL':
            exploratory=[dict(metric='prediction.numeric-mae',population=online[('load_ratio','seed')],window=whole)]
        profiles.append(dict(id=identity,family=family,protocol=protocol,metric_populations=mapping,
                             metric_windows=metric_windows,exploratory=exploratory))
    members=[]
    for seed in range(5):
        for family,protocol,variant,training,count,profile in (
                ('A','PREQUENTIAL','seed',0,400,'a-online'),('A','FROZEN_SELECTION_ASSAY','seed',320,80,'a-frozen'),
                ('B','PREQUENTIAL','seed',0,800,'b-online'),('C','FROZEN_SELECTION_ASSAY','contradictory',128,64,'c-frozen'),
                ('D','PREQUENTIAL','seed',0,128,'d-online'),('D','PREQUENTIAL','random-eligible',0,128,'d-online')):
            identity=family.lower()+'-'+('frozen' if family=='A' and training else variant)+'-'+str(seed)
            version=REGISTRIES['family'][family]
            members.append(dict(id=identity,family=family,scenario_version=version,rule_version=version,
                protocol=protocol,variant=variant,seed=seed,training=training,measured=count,profile=profile))
    return validate_plan(dict(schema='b10_analysis_plan_v1',experiment_id='seed-b10-default-v1',experiment_version=1,
        analysis_plan_version=1,members=members,metrics=[dict(id=m,version=REGISTRIES['metric'][m]) for m in METRICS],
        seeds=list(range(5)),populations=populations,windows=[dict(id=i,start=a,end=b,unit='ordinal') for i,a,b in window_definitions],
        baselines=[dict(id='persistence',version=1),dict(id='global-history',version=1)],
        exclusions=['invalid_observation','insufficient_support','not_applicable'],eligibility='registered_support',
        coverage='all_opportunities',aggregation='ordered_fsum',standardization='equal_qualifying_actions',
        missing_rules='unavailable_with_reason',thresholds=[],questions=[dict(id='registered-descriptive-evidence',
        metrics=list(METRICS),rule='descriptive_only',reason='DESCRIPTIVE_ONLY_NO_CLASSIFICATION_RULE')],
        exploratory=True,inventory_profiles=profiles))


def analysis_digest(plan):
    return hashlib.sha256(b'SEED_B10_ANALYSIS_PLAN_V1\0' + canonical_bytes(strict_json(plan.body, max_bytes=128*1024))).hexdigest()


def _identity(plan):
    p = strict_json(plan.body, max_bytes=128*1024)
    return p['experiment_id'] + '-' + str(p['experiment_version']) + '-' + str(p['analysis_plan_version'])


def _read(capability, kind, identity, maximum):
    fd = capability.open(kind, identity, 'read')
    with os.fdopen(fd, 'rb') as f:
        value = f.read(maximum + 1)
    if len(value) > maximum:
        raise ContractError()
    return value


def freeze_plan(plan, capability):
    p = validate_plan(strict_json(plan.body, max_bytes=128*1024))
    digest = analysis_digest(p)
    body = canonical_bytes(strict_json(p.body, max_bytes=128*1024))
    receipt = raw_bytes({'schema':'b10_plan_freeze_v1','digest':digest,'body_sha256':hashlib.sha256(body).hexdigest(),
                        'identity':_identity(p),'frozen_before_execution':True,
                        'first_members':[[m['id'],'training' if m['training'] else 'measured',1]
                                         for m in strict_json(p.body, max_bytes=128*1024)['members']]})
    if hasattr(capability,'admit_control'):
        capability.admit_control(len(body)+len(receipt))
    try:
        # Reserve the immutable version identity first, but never expose a valid
        # receipt until the body and directory entry have been fsynced.
        receipt_fd = capability.open('freeze', _identity(p), 'create')
        with os.fdopen(receipt_fd, 'wb') as out:
            body_fd = capability.open('plan', digest, 'create')
            with os.fdopen(body_fd, 'wb') as f:
                f.write(body)
                f.flush()
                os.fsync(f.fileno())
            capability.sync()
            out.write(receipt)
            out.flush()
            os.fsync(out.fileno())
        capability.sync()
        return FrozenPlan(p, digest, receipt)
    except OSError:
        raise ContractError() from None


def require_frozen(plan, capability):
    p = validate_plan(strict_json(plan.body, max_bytes=128*1024))
    digest = analysis_digest(p)
    try:
        raw = _read(capability, 'freeze', _identity(p), 16*1024)
        receipt = strict_json(raw, max_bytes=16*1024)
        fields(receipt, ('schema','digest','body_sha256','identity','frozen_before_execution','first_members'))
        body = _read(capability, 'plan', digest, 128*1024)
        expected = canonical_bytes(strict_json(p.body, max_bytes=128*1024))
        if (receipt['schema'] != 'b10_plan_freeze_v1' or receipt['identity'] != _identity(p) or receipt['digest'] != digest
                or receipt['frozen_before_execution'] is not True or body != expected
                or receipt['body_sha256'] != hashlib.sha256(body).hexdigest()
                or receipt['first_members'] != [[m['id'],'training' if m['training'] else 'measured',1]
                                               for m in strict_json(p.body, max_bytes=128*1024)['members']]):
            raise ContractError()
        return FrozenPlan(p, digest, raw)
    except OSError:
        raise ContractError() from None
