"""Join bounded, original post-ACK measurement evidence to its checkpoint."""
import math
import re
import sys

from .contracts import ContractError
from .registry import ACTIONS
from .specs import raw_bytes


def _baseline_links(baselines, history, action, before):
    if (type(baselines) is not dict
            or set(baselines) != {'history', 'action', 'persistence', 'global-history'}
            or baselines['action'] != action):
        raise ContractError()
    source = baselines['history']
    if (type(source) is not dict or set(source) != {
            'cutoff_transition_id', 'raw_rows_examined', 'raw_ids',
            'source_digest', 'reason'}
            or type(source['cutoff_transition_id']) is not type(history['cutoff_transition_id'])
            or source['cutoff_transition_id'] != history['cutoff_transition_id']
            or type(source['raw_rows_examined']) is not int
            or source['raw_rows_examined'] != history['raw_rows_examined']
            or source['reason'] is not None
            or type(source['source_digest']) is not str
            or not re.fullmatch('[0-9a-f]{64}', source['source_digest'])):
        raise ContractError()
    ids = source['raw_ids']
    if (type(ids) is not list or len(ids) != source['raw_rows_examined']
            or len(ids) > 200
            or any(type(i) is not int or not 1 <= i <= history['cutoff_transition_id']
                   for i in ids)
            or ids != sorted(set(ids), reverse=True)):
        raise ContractError()
    # Persistence is fully determined by the recorded pre-action observation.
    # Audit it independently: neither outcomes nor learned state enter this
    # reference. Global-history arithmetic still needs its original raw pool.
    from .baselines import forecast_baselines
    persistence = forecast_baselines(before, action, (), None)['persistence']
    if raw_bytes(baselines['persistence']) != raw_bytes(persistence):
        raise ContractError()
    forecast = baselines['global-history']
    if (type(forecast) is not dict or set(forecast) != {'signals'}
            or type(forecast['signals']) is not dict
            or set(forecast['signals']) != set(persistence['signals'])):
        raise ContractError()
    for target, signal in forecast['signals'].items():
        current = persistence['signals'][target]
        if current['status'] == 'unavailable':
            if raw_bytes(signal) != raw_bytes(current):
                raise ContractError()
            continue
        if type(signal) is not dict or signal.get('status') != 'predicted':
            raise ContractError()
        method = signal.get('method')
        network = target == 'network_reachable'
        supported_method = 'global_boolean_frequency' if network else 'global_mean_delta'
        fields = {'status', 'value', 'method', 'evidence_count', 'source_ids',
                  'clamped', 'candidate_source_ids', 'candidate_usable_count', 'reason'}
        if network and method == supported_method:
            fields.add('probability_true')
        if set(signal) != fields or method not in ('persistence', supported_method):
            raise ContractError()
        count, sources = signal['evidence_count'], signal['source_ids']
        candidates = signal['candidate_source_ids']
        if (type(count) is not int or not 0 <= count <= 200
                or type(sources) is not list or len(sources) != count
                or type(candidates) is not list or len(candidates) > 200
                or type(signal['candidate_usable_count']) is not int
                or signal['candidate_usable_count'] != len(candidates)
                or any(type(i) is not int or i not in ids for i in sources + candidates)
                or candidates != sorted(set(candidates), reverse=True)
                or type(signal['clamped']) is not bool):
            raise ContractError()
        if method == 'persistence':
            if (count != 0 or len(candidates) >= 2 or signal['clamped']
                    or signal['reason'] != 'INSUFFICIENT_SUPPORT'
                    or raw_bytes(signal['value']) != raw_bytes(current['value'])):
                raise ContractError()
            continue
        if count < 2 or sources != candidates or signal['reason'] is not None:
            raise ContractError()
        value = signal['value']
        if network:
            probability = signal['probability_true']
            if (type(value) is not bool or type(probability) not in (int, float)
                    or not math.isfinite(probability) or not 0 <= probability <= 1
                    or value != (probability >= .5) or signal['clamped']):
                raise ContractError()
        else:
            ceiling = sys.float_info.max if target == 'load_ratio' else 100.
            if (type(value) not in (int, float) or not math.isfinite(value)
                    or not 0 <= value <= ceiling
                    or signal['clamped'] and value not in (0., ceiling)):
                raise ContractError()


def join_checkpoint(checkpoint, body):
    """Return metric input without learner inference or reading live state.

    A missing sidecar is legacy missing provenance. It never creates zero
    baselines, an empty-history claim, or reconstructed candidate predictions.
    """
    if type(body) is not dict or 'measurement_evidence' not in body:
        return checkpoint
    sidecar = body['measurement_evidence']
    if (body.get('acked') is not True or type(sidecar) is not dict
            or set(sidecar) != {'schema', 'selection', 'unselected_predictions',
                               'baselines', 'baseline_unavailable_reason'}
            or sidecar['schema'] != 'b10_postack_measurement_v1'):
        raise ContractError()
    from seed.decision_record import (
        TARGETS, compact, validate_record, validate_prediction)
    selection = sidecar['selection']
    action = checkpoint['selected_action']
    prediction = checkpoint['prediction']
    try:
        validate_record(selection, prediction=prediction,
                        state_before=checkpoint['state_before'], draft=True)
        history = selection['history']
        if (selection['selected_action'] != action
                or body.get('decision_id') != selection['decision_id']
                or history['cutoff_transition_id'] !=
                (checkpoint['history_cutoff_id'] or None)):
            raise ContractError()
        unselected = sidecar['unselected_predictions']
        if type(unselected) is not dict or set(unselected) != set(ACTIONS) - {action}:
            raise ContractError()
        for candidate_action, candidate in unselected.items():
            validate_prediction(candidate, candidate_action)
            forecasts = selection['candidates'][candidate_action]['resource_forecasts']
            for target in TARGETS:
                declared, full = forecasts[target], candidate['signals'][target]
                if (any(declared[field] != full.get(field)
                        for field in ('value', 'method', 'evidence_count', 'confidence'))
                        or compact(declared['value']) != compact(full.get('value'))):
                    raise ContractError()
        baselines = sidecar['baselines']
        reason = sidecar['baseline_unavailable_reason']
        if history['status'] == 'unavailable':
            if baselines is not None or reason != history['reason']:
                raise ContractError()
        else:
            if reason is not None:
                raise ContractError()
            _baseline_links(baselines, history, action, checkpoint['state_before'])
        capture = dict(
            selection=selection, history=history, selected_action=action,
            state_before=checkpoint['state_before'],
            selected_prediction=prediction,
            candidate_predictions={action: prediction, **unselected})
        return dict(checkpoint=checkpoint, capture=capture,
                    baselines=baselines if baselines is not None else {},
                    updates=body.get('updates', {}))
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        raise ContractError() from None
