"""Literal losses, paired populations and action-exposure adaptation."""
from collections import Counter
import math

from ..contracts import CompletedEvidence, ContractError, strict_json, validate_event_key
from ..registry import ACTIONS, WINDOWS
from ..analysis import inventory_metadata
from .registry import measured, resolve

PREDICTION_METRICS = ('prediction.numeric-mae', 'prediction.numeric-normalized-mae',
    'prediction.boolean-accuracy', 'prediction.boolean-brier', 'prediction.coverage',
    'prediction.support-counts', 'prediction.window-change', 'prediction.adaptation-delay')


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def _rows(evidence, phase):
    if type(evidence) is not tuple or len(evidence) > 1024:
        raise ContractError()
    result, seen = [], set()
    for item in evidence:
        if type(item) is not CompletedEvidence:
            raise ContractError()
        key = validate_event_key(list(item.key))
        if key[:3] in seen:
            raise ContractError()
        seen.add(key[:3])
        raw = strict_json(item.body)
        if type(raw) is not dict:
            raise ContractError()
        if key[0] != phase:
            continue
        data, capture = raw.get('checkpoint', raw), raw.get('capture', raw)
        if type(data) is not dict or type(capture) is not dict:
            raise ContractError()
        selection = capture.get('selection', {})
        action = data.get('selected_action', capture.get('selected_action', selection.get('selected_action')))
        prediction = data.get('prediction', capture.get('selected_prediction', {}))
        after = data.get('state_after', capture.get('state_after', {}))
        if any(type(x) is not dict for x in (prediction, after, selection)):
            raise ContractError()
        result.append(dict(ordinal=key[2], subcase=key[1], action=action, prediction=prediction,
            after=after, baselines=raw.get('baselines', {}),
            # Checkpoint v1 encodes empty history as zero; B8/baselines use
            # None. Normalize only this metric view, never the stored evidence.
            cutoff=data.get('history_cutoff_id', selection.get('history', capture.get('history', {})).get('cutoff_transition_id')) or None,
            candidates=capture.get('candidate_predictions', {})))
    result.sort(key=lambda r: (r['ordinal'], r['subcase']))
    return result


def _signal(row, method, target):
    if method != 'seed' and 'history' in row['baselines']:
        if (row['baselines']['history'].get('cutoff_transition_id') != row['cutoff']
                or row['baselines'].get('action') != row['action']):
            raise ContractError()
    prediction = row['prediction'] if method == 'seed' else row['baselines'].get(method, {})
    return prediction.get('signals', {}).get(target, {})


def _loss(row, method, target, metric, stratum):
    signal = _signal(row, method, target)
    observed = row['after'].get('network' if target == 'network_reachable' else target)
    if signal.get('status') != 'predicted':
        return None, 'prediction_unavailable'
    if stratum == 'action_mean' and method == 'seed' and (signal.get('method') != 'action_mean_delta'
            or type(signal.get('evidence_count')) is not int or signal['evidence_count'] < 2):
        return None, 'insufficient_action_support'
    value = signal.get('value')
    if target == 'network_reachable':
        if type(observed) is not bool:
            return None, 'outcome_unavailable'
        if type(value) is not bool:
            return None, 'prediction_invalid'
        if metric == 'prediction.boolean-brier':
            probability = signal.get('probability_true')
            if (not _finite(probability) or not 0 <= probability <= 1
                    or signal.get('method') not in ('action_boolean_frequency','global_boolean_frequency')
                    or type(signal.get('evidence_count')) is not int or signal['evidence_count'] < 2):
                return None, 'probability_unavailable'
            return (probability-int(observed))**2, 'eligible'
        return float(value == observed), 'eligible'
    if not _finite(observed) or observed < 0 or (target != 'load_ratio' and observed > 100):
        return None, 'outcome_unavailable'
    if not _finite(value) or value < 0 or (target != 'load_ratio' and value > 100):
        return None, 'prediction_invalid'
    loss = abs(value-observed)
    if metric == 'prediction.numeric-normalized-mae':
        loss /= 1 if target == 'load_ratio' else 100
    return loss, 'eligible'


def _ordinal_detail(values):
    if len(values)<=32:return values
    ranges=[]
    for value in values:
        if ranges and value==ranges[-1][1]+1:ranges[-1][1]=value
        else:ranges.append([value,value])
    return dict(encoding='inclusive_ranges',count=len(values),ranges=ranges)


def _support_detail(counts):
    if len(counts)<=32:return dict(counts)
    ranges=[]
    for key,count in sorted(((int(k),v) for k,v in counts.items() if k!='unavailable')):
        if ranges and key==ranges[-1][1]+1 and count==ranges[-1][2]:ranges[-1][1]=key
        else:ranges.append([key,key,count])
    return dict(encoding='inclusive_support_ranges_with_count',ranges=ranges,unavailable=counts.get('unavailable',0))


def _paired(rows, definition, target, metric):
    method, baseline = definition.get('method','seed'), definition.get('comparison')
    values, counterpart, sources = [], [], []
    counts = Counter(dict(both=0, seed_only=0, baseline_only=0, neither=0))
    reasons, strata, methods, support = Counter(), {}, Counter(), Counter()
    usable = Counter()
    for row in rows:
        loss, reason = _loss(row, method, target, metric, definition.get('stratum','all_methods'))
        other, other_reason = (loss, reason) if baseline is None else _loss(row, baseline, target, metric, 'all_methods')
        usable[method] += loss is not None
        if baseline is not None: usable[baseline] += other is not None
        label = 'both' if loss is not None and other is not None else 'seed_only' if loss is not None else 'baseline_only' if other is not None else 'neither'
        counts[label] += 1
        reasons[reason + '|' + other_reason] += 1
        action = row['action'] if row['action'] in ACTIONS else 'unknown'
        stratum = strata.setdefault(action, dict(opportunities=0, paired=0))
        stratum['opportunities'] += 1
        stratum['paired'] += label == 'both'
        signal = _signal(row, method, target)
        methods[signal.get('method','unavailable')] += 1
        n = signal.get('evidence_count')
        support[str(n) if type(n) is int and n >= 0 else 'unavailable'] += 1
        if label == 'both':
            stratum.setdefault('_losses',[]).append(loss)
            stratum.setdefault('_baseline_losses',[]).append(other)
            values.append(loss); counterpart.append(other); sources.append(row['ordinal'])
    n = len(rows)
    coverage = {method: usable[method]/n if n else None}
    if baseline is not None: coverage[baseline] = usable[baseline]/n if n else None
    for stratum in strata.values():
        stratum['numerator']=math.fsum(stratum.pop('_losses',[]))
        stratum['baseline_numerator']=math.fsum(stratum.pop('_baseline_losses',[]))
        stratum['value']=stratum.get('numerator',0.)/stratum['paired'] if stratum['paired'] >= 5 else None
        stratum['baseline_value']=stratum.get('baseline_numerator',0.)/stratum['paired'] if stratum['paired'] >= 5 and baseline is not None else None
        stratum['reason']=None if stratum['paired']>=5 else 'INSUFFICIENT_EVIDENCE'
    return values, counterpart, dict(opportunities=n, numerator=math.fsum(values), baseline_numerator=math.fsum(counterpart), denominator=len(values),
        source_ordinals=_ordinal_detail(sources), coverage=coverage, eligibility_cross_tab=dict(counts),
        reason_cross_tab=dict(reasons), action_strata=strata, methods=dict(methods),
        method_support=_support_detail(support), exclusions=n-len(values))


def _window_change(rows, definition, target, family):
    windows = WINDOWS.get(family)
    if windows is None:
        return None, dict(qualifying_actions=[], reason='NOT_APPLICABLE_TO_REGISTERED_PROTOCOL_OR_FAMILY')
    early, late = windows[0], windows[-1]
    per_action, natural, qualifying, excluded = {}, {}, [], {}
    natural_counts={}
    for action in ACTIONS:
        scores = []
        for start, end in (early, late):
            group = [r for r in rows if start <= r['ordinal'] <= end and r['action'] == action]
            values, _, _ = _paired(group, definition, target, 'prediction.numeric-mae')
            scores.append(values)
        if all(len(v) >= 5 for v in scores):
            qualifying.append(action)
            per_action[action] = dict(early=math.fsum(scores[0])/len(scores[0]), late=math.fsum(scores[1])/len(scores[1]),
                                     early_count=len(scores[0]), late_count=len(scores[1]))
        else:
            excluded[action] = dict(reason='INSUFFICIENT_EVIDENCE', early_count=len(scores[0]), late_count=len(scores[1]))
    qualifying.sort()
    for name, (start, end) in (('early', early), ('late', late)):
        group = [r for r in rows if start <= r['ordinal'] <= end]
        values, _, _ = _paired(group, definition, target, 'prediction.numeric-mae')
        natural[name] = math.fsum(values)/len(values) if values else None
        natural_counts[name]=len(values)
    standardized = {name: math.fsum(per_action[a][name] for a in qualifying)/len(qualifying) if qualifying else None for name in ('early','late')}
    return (standardized['early']-standardized['late'] if qualifying else None), dict(
        qualifying_actions=qualifying, excluded_actions=excluded, per_action=per_action,
        standardized=standardized, natural_action_mix=natural, natural_paired_counts=natural_counts, windows=[list(early),list(late)],
        reason=None if qualifying else 'INSUFFICIENT_EVIDENCE')


def _adaptation(rows):
    boundary = next((r for r in rows if r['ordinal'] == 321), None)
    candidate = boundary['candidates'].get('rest', {}).get('signals', {}).get('load_ratio', {}) if boundary else {}
    rest = [r for r in rows if r['ordinal'] >= 321 and r['action'] == 'rest']
    losses = [_loss(r, 'seed', 'load_ratio', 'prediction.numeric-mae', 'action_mean')[0] for r in rest]
    usable = sum(v is not None for v in losses)
    facts = dict(observed_rest_exposures=len(rest), observed_postshift_transitions=sum(r['ordinal']>=321 for r in rows),
                 registered_postshift_transition_horizon=480, prechange_candidate=candidate,
                 paired_usable_rest_samples=usable, rest_coverage=usable/len(rest) if rest else None,
                 first_postshift_rest_ordinal=rest[0]['ordinal'] if rest else None,
                 first_postshift_rest_loss=losses[0] if losses else None,
                 first_five_rest_exposure_losses=losses[:5])
    if (candidate.get('method') != 'action_mean_delta' or candidate.get('status') != 'predicted'
            or type(candidate.get('evidence_count')) is not int or candidate['evidence_count'] < 2):
        return None, 'INSUFFICIENT_PRECHANGE_EVIDENCE', facts
    windows, eligible_streak, passing_streak, eligible_sequence = [], [], [], False
    for start in range(0, len(rest)-4, 5):
        group = rest[start:start+5]
        losses = [_loss(r, 'seed', 'load_ratio', 'prediction.numeric-mae', 'action_mean')[0] for r in group]
        qualified = all(v is not None for v in losses)
        mae = math.fsum(losses)/5 if qualified else None
        window = dict(start_exposure=start+1, end_exposure=start+5, end_ordinal=group[-1]['ordinal'],
                      paired_count=sum(v is not None for v in losses), mae=mae,
                      status='qualified' if qualified else 'unavailable')
        windows.append(window)
        eligible_streak = eligible_streak+[window] if qualified else []
        eligible_sequence |= len(eligible_streak) >= 3
        passing_streak = passing_streak+[window] if qualified and mae <= .02 else []
        if len(passing_streak) >= 3:
            facts['exposure_windows'] = windows
            return dict(event='observed', rest_exposures=start+5,
                completed_transition_delay=group[-1]['ordinal']-320,
                confirmation_windows=passing_streak[-3:]), None, facts
    facts['exposure_windows'] = windows
    if not eligible_sequence:
        return None, 'INSUFFICIENT_EVIDENCE', facts
    return dict(event='not_observed', right_censored_rest_exposures=len(rest),
        right_censored_completed_transitions=max((r['ordinal']-320 for r in rows if r['ordinal']>=321),default=0),
        registered_postshift_transition_horizon=480), None, facts


def measure_prediction(metric_id, evidence, population, plan):
    if metric_id not in PREDICTION_METRICS:
        raise ContractError()
    _, _, member, definition, window, dimensions = resolve(metric_id, population, plan)
    carrier = _rows(evidence, definition['phase'])
    carrier = [r for r in carrier if window['start']<=r['ordinal']<=window['end']
        and (definition.get('variant') is None or r['subcase']==definition['variant'])]
    rows = [r for r in carrier if window['start'] <= r['ordinal'] <= window['end']
            and (definition['action'] == 'all' or r['action'] == definition['action'])
            and (definition.get('variant') is None or r['subcase']==definition['variant'])]
    target = 'network_reachable' if definition['signal'] == 'network' else definition['signal']
    if metric_id == 'prediction.adaptation-delay':
        if not inventory_metadata(member,metric_id,definition,window)['applicable']:
            return measured(metric_id, population, plan, state='NOT_EVALUATED', reason='NOT_APPLICABLE_TO_REGISTERED_PROTOCOL_OR_FAMILY')
        # Qualification uses the pre-selection candidate even if the population
        # is rest-only; never erase non-rest transition321's captured candidate.
        value, reason, facts = _adaptation(carrier)
        facts.update(measurement_action='rest',measurement_method='seed_action_mean_delta_support_at_least_2',
            qualification_ordinal=321,carrier_action=definition['action'],
            completed_transition_context='all_actions_within_registered_whole_horizon')
        return measured(metric_id, population, plan, value=value, reason=reason, unit='rest_exposure', **facts)
    numeric = metric_id in ('prediction.numeric-mae','prediction.numeric-normalized-mae','prediction.window-change')
    boolean = metric_id in ('prediction.boolean-accuracy','prediction.boolean-brier')
    if target not in ('battery_pct','load_ratio','disk_free_pct','network_reachable') or (numeric and target=='network_reachable') or (boolean and target!='network_reachable'):
        return measured(metric_id, population, plan, state='NOT_EVALUATED', reason='NOT_APPLICABLE_TO_REGISTERED_SIGNAL')
    if metric_id == 'prediction.window-change':
        if member['protocol'] != 'PREQUENTIAL':
            return measured(metric_id, population, plan, state='NOT_EVALUATED', reason='NOT_APPLICABLE_TO_REGISTERED_PROTOCOL_OR_FAMILY')
        value, facts = _window_change(rows, definition, target, member['family'])
        reason = facts.pop('reason')
        return measured(metric_id, population, plan, value=value, reason=reason, unit='early_minus_late_mae', **facts)
    scoring = metric_id if numeric or boolean else 'prediction.boolean-accuracy' if target=='network_reachable' else 'prediction.numeric-mae'
    values, counterpart, facts = _paired(rows, definition, target, scoring)
    if metric_id == 'prediction.coverage':
        value = facts['coverage'] if rows else None
    elif metric_id == 'prediction.support-counts':
        value = dict(methods=facts['methods'], support=facts['method_support']) if rows else None
    else:
        value = math.fsum(values)/len(values) if values else None
        if (definition['action'] != 'all' or definition.get('stratum') == 'action_mean') and len(values) < 5:
            value = None
    minimum=5 if definition['action']!='all' or definition.get('stratum')=='action_mean' else 1
    facts['summary_minimum_paired']=minimum
    facts['baseline_value'] = math.fsum(counterpart)/len(counterpart) if len(counterpart)>=minimum and definition.get('comparison') else None
    unit = ('count' if metric_id == 'prediction.support-counts' else
            'fraction' if boolean or metric_id in ('prediction.coverage','prediction.numeric-normalized-mae') else
            'load_ratio' if target == 'load_ratio' else 'percentage_points')
    return measured(metric_id, population, plan, value=value, reason=None if value is not None else 'INSUFFICIENT_EVIDENCE',
                    unit=unit, **facts)
