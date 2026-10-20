"""Post-ACK evidence joins use literal captured facts, not fresh predictions."""
import copy
import json

import pytest

from development.evaluation import artifacts
from development.evaluation.analysis import freeze_plan, validate_plan
from development.evaluation.contracts import ContractError, PreUpdateEvidence
from .test_analysis import ClosedRoot


def captured(tmp_path, *, ordinal=1):
    from seed.memory import Memory
    from seed.learner import Learner, ACTIONS
    from seed.predictor import Predictor
    from seed.decision import DecisionSystem
    from development.evaluation.baselines import forecast_baselines
    from development.evaluation.checkpoint import ScoreJournal
    from development.evaluation.paths import EvaluationRoot
    from tests.test_decision import RNG
    from tests.test_predictor import history
    before = dict(battery_pct=80, charging=False, load_ratio=.5,
                  disk_free_pct=50, network=True, local_hour=12)
    memory = Memory(tmp_path / 'source.sqlite3')
    try:
        for _ in range(2):
            history(memory, before, dict(before, load_ratio=.4), 'rest')
        system = DecisionSystem(memory, Predictor(memory),
                                Learner(memory, epsilon=1), rng=RNG(draw=0))
        prepared = system.prepare(before, selected_at=100)
        selected = system.select(prepared)
        assert selected.decision.action == 'observe'
        raw_history = tuple(dict(row) for row in memory.db.execute(
            'SELECT * FROM transitions ORDER BY id DESC LIMIT 200'))
        baselines = forecast_baselines(before, 'observe', raw_history, 2)
        checkpoint = dict(
            phase='measured', subcase='default', transition_ordinal=ordinal,
            history_cutoff_id=2, state_before=before, selected_action='observe',
            prediction=selected.prediction, state_after=dict(before, load_ratio=.55))
        sidecar = dict(
            schema='b10_postack_measurement_v1', selection=selected.record,
            unselected_predictions={a: prepared['batch'].predictions[a]
                                    for a in ACTIONS if a != 'observe'},
            baselines=baselines, baseline_unavailable_reason=None)
        event = dict(key=['measured', 'default', ordinal, 'update'],
                     body=dict(acked=True, execution='completed', updates={},
                               decision_id=selected.record['decision_id'],
                               measurement_evidence=sidecar))
        journal = ScoreJournal.create(EvaluationRoot.create(tmp_path), 'a' * 32)
        try:
            frame = journal.frame(PreUpdateEvidence(json.dumps(checkpoint).encode()))
            line = json.dumps(dict(header=json.loads(frame.header),
                                   evidence=json.loads(frame.evidence.body))).encode() + b'\n'
            return artifacts._journal_frames(line), event
        finally:
            journal.close()
    finally:
        memory.close()


def frozen(tmp_path, plan_body, *, adaptation=False):
    from development.evaluation.registry import REGISTRIES
    body = copy.deepcopy(plan_body)
    metric = 'prediction.adaptation-delay' if adaptation else 'prediction.numeric-mae'
    body['metrics'] = [dict(id=metric, version=REGISTRIES['metric'][metric])]
    body['questions'][0]['metrics'] = [metric]
    body['populations'][0]['method'] = 'seed' if adaptation else 'persistence'
    if adaptation:
        body['members'][0].update(family='B', measured=800)
        body['windows'][0]['end'] = 800
    path = tmp_path / 'plan'
    path.mkdir()
    return freeze_plan(validate_plan(body), ClosedRoot(path))


def test_artifact_metrics_score_the_captured_baseline(tmp_path, plan_body):
    plan = frozen(tmp_path, plan_body)
    frames, event = captured(tmp_path)
    metric = 'prediction.numeric-mae'
    value = abs(.55 - .5)
    expected = dict(identity=f'member-0:{metric}:all:whole', metric=metric,
                    version=1, member='member-0', state='MEASURED',
                    value=value, reason=None)
    record = dict(events=[event], checkpoints=[], measurements=[expected],
                  findings=[dict(question='prediction', status='NOT_EVALUATED',
                                 reason='DESCRIPTIVE_ONLY_NO_CLASSIFICATION_RULE',
                                 execution='COMPLETED')])
    metrics = json.loads(artifacts._metrics(record, plan, 'COMPLETED', None, frames, []))
    assert metrics['produced'] == [expected]


def test_unselected_prechange_candidate_reaches_adaptation(tmp_path, plan_body):
    plan = frozen(tmp_path, plan_body, adaptation=True)
    frames, event = captured(tmp_path, ordinal=321)
    rows, _ = artifacts.derive_scientific_outputs(
        plan, frames, [], 'COMPLETED', post_ack_events=[event])
    # A supported rest candidate was captured although observe was selected.
    # There are no postshift rest exposures: that, rather than missing
    # prechange evidence, is the honest reason for no adaptation result.
    assert rows[0]['state'] == 'UNAVAILABLE'
    assert rows[0]['reason'] == 'INSUFFICIENT_EVIDENCE'


@pytest.mark.parametrize('defect', [
    'cutoff', 'action', 'candidate-action', 'selected-copy',
    'decision-id', 'baseline-cutoff', 'baseline-action', 'duplicate', 'orphan',
    'candidate-value', 'baseline-future-source',
])
def test_postack_join_rejects_misbound_evidence(tmp_path, plan_body, defect):
    plan = frozen(tmp_path, plan_body)
    frames, event = captured(tmp_path)
    sidecar = event['body']['measurement_evidence']
    if defect == 'cutoff':
        sidecar['selection']['history']['cutoff_transition_id'] = 1
    elif defect == 'action':
        sidecar['selection']['selected_action'] = 'rest'
    elif defect == 'candidate-action':
        sidecar['unselected_predictions']['rest']['action'] = 'observe'
    elif defect == 'candidate-value':
        sidecar['unselected_predictions']['rest']['signals']['load_ratio']['value'] = .35
    elif defect == 'selected-copy':
        sidecar['unselected_predictions']['observe'] = copy.deepcopy(
            sidecar['unselected_predictions']['rest'])
    elif defect == 'decision-id':
        event['body']['decision_id'] = '0' * 32
    elif defect == 'baseline-cutoff':
        sidecar['baselines']['history']['cutoff_transition_id'] = 1
    elif defect == 'baseline-action':
        sidecar['baselines']['action'] = 'rest'
    elif defect == 'baseline-future-source':
        sidecar['baselines']['global-history']['signals']['load_ratio']['source_ids'] = [2, 3]
    elif defect == 'orphan':
        event['key'][2] = 2
    events = [event, copy.deepcopy(event)] if defect == 'duplicate' else [event]
    with pytest.raises(ContractError):
        artifacts.derive_scientific_outputs(
            plan, frames, [], 'COMPLETED', post_ack_events=events)


def test_legacy_missing_sidecar_remains_unavailable(tmp_path, plan_body):
    plan = frozen(tmp_path, plan_body)
    frames, event = captured(tmp_path)
    del event['body']['measurement_evidence']
    rows, _ = artifacts.derive_scientific_outputs(
        plan, frames, [], 'COMPLETED', post_ack_events=[event])
    assert rows[0]['state'] == 'UNAVAILABLE'
    assert rows[0]['value'] is None


@pytest.mark.parametrize('defect', [
    'persistence-outcome', 'missing-method', 'unknown-method', 'extra-field',
    'negative-load', 'percent-overflow', 'numeric-bool', 'clamped-int',
    'unsupported-global', 'wrong-reason', 'false-unavailable',
    'probability-range', 'probability-bool', 'probability-decision',
    'source-count', 'reordered-source', 'extra-probability',
])
def test_artifact_rejects_invalid_baseline_forecasts(tmp_path, plan_body, defect):
    plan = frozen(tmp_path, plan_body)
    frames, event = captured(tmp_path)
    baselines = event['body']['measurement_evidence']['baselines']
    persistence = baselines['persistence']['signals']['load_ratio']
    signal = baselines['global-history']['signals']['load_ratio']
    boolean = baselines['global-history']['signals']['network_reachable']
    if defect == 'persistence-outcome':
        persistence['value'] = .55
    elif defect == 'missing-method':
        del signal['method']
    elif defect == 'unknown-method':
        signal['method'] = 'unknown'
    elif defect == 'extra-field':
        signal['unexpected'] = True
    elif defect == 'negative-load':
        signal['value'] = -.1
    elif defect == 'percent-overflow':
        baselines['global-history']['signals']['battery_pct']['value'] = 101
    elif defect == 'numeric-bool':
        signal['value'] = True
    elif defect == 'clamped-int':
        signal['clamped'] = 0
    elif defect == 'unsupported-global':
        signal.update(evidence_count=0, source_ids=[])
    elif defect == 'wrong-reason':
        signal['reason'] = 'INSUFFICIENT_SUPPORT'
    elif defect == 'false-unavailable':
        baselines['global-history']['signals']['load_ratio'] = dict(
            status='unavailable', value=None, evidence_count=0,
            source_ids=[], reason='missing_current_value')
    elif defect == 'probability-range':
        boolean['probability_true'] = 1.5
    elif defect == 'probability-bool':
        boolean['probability_true'] = True
    elif defect == 'probability-decision':
        boolean['value'] = False
    elif defect == 'source-count':
        signal['candidate_usable_count'] = 0
    elif defect == 'reordered-source':
        signal['source_ids'].reverse()
    elif defect == 'extra-probability':
        signal['probability_true'] = .5
    with pytest.raises(ContractError):
        artifacts.derive_scientific_outputs(
            plan, frames, [], 'COMPLETED', post_ack_events=[event])
